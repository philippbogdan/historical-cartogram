# Population as mass: what survives

As of 2026-08-28. Source: a conversation (Phil's intuition, a ChatGPT reply, my corrections).

## The object underneath everything

Give the Mercator rectangle the metric  g = (rho / rho_bar) (dx^2 + dy^2).
Areas in g are people; angles in g are geographic. This "population manifold" is the
conformal cartogram: it exists, but it is curved, K = -(rho_bar / 2 rho) laplacian(log(rho/rho_bar)),
so it cannot be drawn flat without distorting angles. Every cartogram method is a way of
flattening it, and the methods differ only in which flattening cost they pay
(OT: displacement; quasiconformal: angle distortion; diffusion and flow methods: none, a process).

## Three flows that all end at uniform density

Write delta = (rho - rho_bar) / rho_bar and let Phi solve  laplacian(Phi) = delta  with
no-flux (Neumann) walls; the mean must be subtracted for this to be solvable, the same
reason cosmology sources gravity with the density contrast.

```
                 velocity field            potential            what it is
 diffusion       v = -grad(log rho)        local                 W2 gradient flow of entropy
                                                                 (Gastner-Newman 2004)
 flow-based      v = -grad(Phi) / rho_t    Poisson, solved once  least-effort flow along the
 (GSM 2018)      rho_t = linear mix of                           LINEAR path rho_0 -> rho_bar
                 rho_0 and rho_bar                               (verified: arXiv 1802.07625, eq 5)
 anti-gravity    v = +grad(Phi_t)          Poisson, re-solved    W2 gradient flow of the Coulomb
 (jellium)       Phi_t from current rho_t  each step             energy with a neutralising background
 OT              straight-line path        Monge-Ampere          W2 geodesic: least effort over
                                                                 ALL paths (Benamou-Brenier)
```

Consequences:

- Phil's "population is negative mass, it explodes" is the anti-gravity row. Run to t -> inf it is
  a density-equalising map (energy 1/2 int |grad Phi|^2 is zero only at rho = rho_bar), so it is a
  cartogram method in its own right. Nobody has published it under that name.
- Gastner-Seguy-More 2018 (go-cart.io) already is a Poisson-potential flow: one Laplace solve of
  the density contrast, then integrate. The gravity intuition reproduces the state of the art.
- The one-shot displacement x -> x + grad(Phi) is the linearisation of the OT (Brenier) map,
  because det(I + D^2 psi) = rho/rho_bar linearises to laplacian(psi) = delta. Iterating the
  Poisson solve (Benamou-Froese-Oberman 2010, method 1) converges to the Monge-Ampere solution,
  i.e. the gravity picture, iterated, is an OT solver we can write with the DCT we already have.
- Positive coupling (attractive gravity) is aggregation (Keller-Segel type): cities collapse to
  points in finite time. That blow-up is the "black hole" in Phil's intuition. Stopped at a finite
  time it is an anti-cartogram: a picture with a free parameter, not a measurement.
- The slider G in [-1, +1]: attractive flow to time tau (G > 0), Earth (0), repulsive flow to
  convergence (G = -1). One artefact contains the anti-cartogram, geography and the cartogram.
- Implementation of the anti-gravity flow = a particle-mesh N-body code with the sign flipped
  and a comoving background: deposit particles (cloud-in-cell), DCT Poisson solve, interpolate
  velocity, RK step. Cosmology codes do exactly this.

## General relativity, properly

- 1+1 GR is trivial (Einstein tensor vanishes identically). That is what "2D GR" usually means
  and it is the objection ChatGPT raised. Phil meant 2D space, i.e. 2+1 gravity, which is not trivial.
- 2+1 gravity (Deser, Jackiw, 't Hooft 1984, from memory): space is flat away from matter; a static
  point mass makes a cone with angle deficit proportional to the mass; static dust gives spatial
  Gaussian curvature proportional to the density. A closed universe needs the total to balance
  (Gauss-Bonnet), which is the mean subtraction again.
- So "population as 2+1 GR mass" = conformal metric e^{2u}(dx^2+dy^2) with -laplacian(u) = kappa (rho - rho_bar) e^{2u}
  (Liouville-type). Positive mass: cities are cones with missing angle, less area around them
  (anti-cartogram). Negative mass: excess angle, more area (cartogram-like). Points do not move;
  geometry changes. To see it you draw geodesics (graticule lines bend around cities like lensing)
  or embed the surface in 3D. This is a "population geometry" side project, not a map warp.

## Discard

Second-order dynamics (points would orbit), the Higgs analogy, extrinsic "dents" as GR, and
"the same skeleton as gravity" beyond first order.
