// MotorGuard feature extraction (portable C++, no Arduino deps). Mirror of ml/features.py.
// N=1024 samples @ 1 kHz, 3 axes in g. Verified against Python by firmware/tests/run_crosscheck.sh
#pragma once
#include <math.h>
#include <stdint.h>

#define MG_N 1024
#define MG_FS 1000.0f

struct MGFeatures {
  float rms, crest, kurt, f_run, a1x, a2x, a3x, r21, e_low, e_mid, e_high, centroid;
};

static inline int mg_kbin(float f) { return (int)(f * MG_N / MG_FS + 0.5f); }

static void mg_fft(float *re, float *im) {  // in-place radix-2, N = MG_N
  const int n = MG_N;
  for (int i = 1, j = 0; i < n; i++) {
    int bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) { float t = re[i]; re[i] = re[j]; re[j] = t; t = im[i]; im[i] = im[j]; im[j] = t; }
  }
  for (int len = 2; len <= n; len <<= 1) {
    float ang = -2.0f * (float)M_PI / len;
    float wr = cosf(ang), wi = sinf(ang);
    for (int i = 0; i < n; i += len) {
      float cr = 1.0f, ci = 0.0f;
      for (int k = 0; k < len / 2; k++) {
        int a = i + k, b = i + k + len / 2;
        float tr = re[b] * cr - im[b] * ci, ti = re[b] * ci + im[b] * cr;
        re[b] = re[a] - tr; im[b] = im[a] - ti;
        re[a] += tr; im[a] += ti;
        float ncr = cr * wr - ci * wi; ci = cr * wi + ci * wr; cr = ncr;
      }
    }
  }
}

// axs: 3 arrays of MG_N floats (g), detrended IN PLACE. scratch: float[2*MG_N], P: float[MG_N/2]
static MGFeatures mg_features(float *axs[3], float *scratch, float *P) {
  MGFeatures f;
  const int n = MG_N;
  double r2max = 0, r2sum = 0, kurt = 0;
  for (int i = 0; i < n / 2; i++) P[i] = 0;
  for (int a = 0; a < 3; a++) {
    float *x = axs[a];
    double m = 0;
    for (int i = 0; i < n; i++) m += x[i];
    m /= n;
    for (int i = 0; i < n; i++) x[i] -= (float)m;
  }
  for (int i = 0; i < n; i++) {
    double r2 = (double)axs[0][i] * axs[0][i] + (double)axs[1][i] * axs[1][i] + (double)axs[2][i] * axs[2][i];
    r2sum += r2; if (r2 > r2max) r2max = r2;
  }
  double rms = sqrt(r2sum / n);
  f.rms = (float)rms;
  f.crest = (float)(sqrt(r2max) / (rms + 1e-12));
  for (int a = 0; a < 3; a++) {
    double v = 0, q = 0;
    for (int i = 0; i < n; i++) { double s = axs[a][i]; v += s * s; q += s * s * s * s; }
    v /= n; q /= n;
    kurt += q / (v * v + 1e-24);
  }
  f.kurt = (float)(kurt / 3.0);
  float *re = scratch, *im = scratch + n;
  for (int a = 0; a < 3; a++) {
    for (int i = 0; i < n; i++) {
      float w = 0.5f * (1.0f - cosf(2.0f * (float)M_PI * i / (n - 1)));
      re[i] = axs[a][i] * w; im[i] = 0;
    }
    mg_fft(re, im);
    for (int k = 0; k < n / 2; k++) P[k] += re[k] * re[k] + im[k] * im[k];
  }
  for (int k = 0; k < n / 2; k++) P[k] = 4.0f * sqrtf(P[k]) / n;  // P now holds amplitude A[k]
  P[0] = 0;
  int lo = mg_kbin(10), hi = mg_kbin(100), kp = lo;
  for (int k = lo; k <= hi; k++) if (P[k] > P[kp]) kp = k;
  f.f_run = kp * MG_FS / MG_N;
  auto amp = [&](int kk) { if (kk + 1 >= n / 2) return 0.0f; float m = P[kk - 1]; if (P[kk] > m) m = P[kk]; if (P[kk + 1] > m) m = P[kk + 1]; return m; };
  f.a1x = amp(kp); f.a2x = amp(2 * kp); f.a3x = amp(3 * kp);
  f.r21 = f.a2x / (f.a1x + 1e-9f);
  double el = 0, em = 0, eh = 0, cn = 0, cd = 0;
  for (int k = mg_kbin(10); k < mg_kbin(100); k++) el += (double)P[k] * P[k];
  for (int k = mg_kbin(100); k < mg_kbin(250); k++) em += (double)P[k] * P[k];
  for (int k = mg_kbin(250); k < n / 2; k++) eh += (double)P[k] * P[k];
  for (int k = mg_kbin(10); k < n / 2; k++) { cn += k * (MG_FS / MG_N) * P[k]; cd += P[k]; }
  f.e_low = (float)el; f.e_mid = (float)em; f.e_high = (float)eh;
  f.centroid = (float)(cn / (cd + 1e-12));
  return f;
}
