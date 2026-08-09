# PHP practices

> **Scope: every repository that contains PHP source files.** These are the
> language-specific practices; the language-agnostic rules live in the
> [repo baseline](repo-baseline.md).

## Syntax lint

- **Every repo that ships `.php` files MUST run `php -l` over all of them as
  a blocking CI gate.**  `php -l` (i.e. `php --syntax-check`) is a built-in
  PHP syntax checker — it parses each file and reports parse errors without
  executing any code.  No custom scanners, no bespoke tooling: the native
  `php -l` gate is deterministic, off-the-shelf, and catches every parse
  error before it reaches production.
- **Canonical example:** [robotsix-website PR #81](https://github.com/damien-robotsix/robotsix-website/pull/81)
  added a `php -l` lint job that runs `find . -name '*.php' -exec php -l {} \;`
  over the repo's PHP source.

## Failure modes prevented

- **Deploying broken PHP.** A parse error in a PHP file — a missing semicolon,
  an unclosed brace, a syntax slip — will cause a runtime fatal error on the
  first request that hits that file.  `php -l` in CI catches every such error
  at PR time, before it can merge.
- **Silent drift.**  Without a lint gate, a PHP file can accumulate parse
  errors across multiple PRs — each passing CI because the file isn't tested —
  and only surface when a production request finally exercises the broken
  code path.
