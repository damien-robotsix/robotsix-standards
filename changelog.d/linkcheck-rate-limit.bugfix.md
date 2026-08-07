Link checking no longer fails on rate-limited hosts. `readthedocs.io` joins the
`ignore_urls` list — four pages link there and it answers anonymous traffic with
429, so an unlucky build failed on all four at once. The MkDocs build integrity
standard now states the general rule: a `403` or `429` means the server answered
and the link is fine, so a checker must never fail on either.
