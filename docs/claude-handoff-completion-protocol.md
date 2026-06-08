# Claude Handoff Completion Protocol

Add this section to every Claude build handoff unless Scott explicitly says the slice is local-only or no-commit.

## Completion Protocol

1. Confirm tests pass:

```text
python -m pytest -q
```

2. Commit only the files for the current slice:

```text
git add <slice files only>
git commit -m "<clear commit message>"
```

3. Push the commit to origin:

```text
git push origin main
```

4. Update the Meridian Obsidian build notes.

Obsidian build folder:

```text
G:\My Drive\Obsidian\Meridian_Build
```

Obsidian sessions folder:

```text
G:\My Drive\Obsidian\Meridian_Sessions
```

The Obsidian update should include:

- build slice name
- summary of changes
- tests run
- commit hash
- push status
- follow-up items

If the working tree contains unrelated uncommitted files, do not include them in the commit.
