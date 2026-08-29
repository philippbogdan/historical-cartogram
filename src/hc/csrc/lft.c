/* Batched 1D discrete Legendre-Fenchel transform (Lucet's linear-time algorithm).
   Row r holds g[i] at coordinates y_i = i + y_off, i < n. For output slopes p_j = j + p_off, j < m:
     out[r][j] = max_i ( p_j * y_i - g[r][i] ),  arg[r][j] = the maximising i.
   Uses the lower convex hull of (y_i, g_i); the maximiser is monotone in p, so one sweep. */
#include <stdlib.h>
void lft_rows(const double* g, int rows, int n, double y_off, int m, double p_off, double* out, int* arg) {
    int* hull = (int*)malloc((size_t)n * sizeof(int));
    for (int r = 0; r < rows; r++) {
        const double* gr = g + (size_t)r * n;
        int h = 0;
        for (int i = 0; i < n; i++) {
            while (h >= 2) {
                int a = hull[h - 2], b = hull[h - 1];
                double s_ab = (gr[b] - gr[a]) / (double)(b - a);
                double s_bi = (gr[i] - gr[b]) / (double)(i - b);
                if (s_ab >= s_bi) h--; else break;
            }
            hull[h++] = i;
        }
        int k = 0;
        double* orow = out + (size_t)r * m;
        int* arow = arg + (size_t)r * m;
        for (int j = 0; j < m; j++) {
            double p = j + p_off;
            while (k + 1 < h) {
                int a = hull[k], b = hull[k + 1];
                double s = (gr[b] - gr[a]) / (double)(b - a);
                if (s < p) k++; else break;
            }
            int i = hull[k];
            orow[j] = p * (i + y_off) - gr[i];
            arow[j] = i;
        }
    }
    free(hull);
}
