// Reads a CSV window (ax,ay,az per line, 1024 lines) and prints the 12 features on one line.
#include <cstdio>
#include "../motorguard_node/mg_features.h"
static float bx[MG_N], by[MG_N], bz[MG_N], sc[2 * MG_N], P[MG_N / 2];
int main(int argc, char **argv) {
  FILE *fp = fopen(argv[1], "r"); if (!fp) return 1;
  for (int i = 0; i < MG_N; i++) if (fscanf(fp, "%f,%f,%f", &bx[i], &by[i], &bz[i]) != 3) return 2;
  float *axs[3] = {bx, by, bz};
  MGFeatures f = mg_features(axs, sc, P);
  printf("%.6f %.6f %.6f %.6f %.6f %.6f %.6f %.6f %.6f %.6f %.6f %.6f\n", f.rms, f.crest, f.kurt, f.f_run, f.a1x, f.a2x, f.a3x, f.r21, f.e_low, f.e_mid, f.e_high, f.centroid);
  return 0;
}
