# honeyau

Data repo for Honeyau (www.honeyau.com, hosted on Lovable).

- `index.html` holds the `seed` block (`<script type="application/json" id="seed">`).
  The live site reads the researched **vesting and pay-timing facts** from it.
  Prices in the seed are not used; the site gets prices live from Yahoo Finance.
- `tools/seed_facts.py` is the only supported way to change the seed
  (`todo`, `apply`, `verify`). It changes fact fields and `as_of` only.
- A weekly scheduled refresh fills missing facts and bumps `as_of`; a checker
  verifies the commit and reverts it if it fails.
- GitHub Pages is off. `tools/make_site.py` is a leftover from the old GitHub Pages setup.
