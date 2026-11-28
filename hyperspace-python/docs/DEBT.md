# Debt

Every shortcut the code knowingly takes, in one place. This is the only
place a shortcut is explained. At the site in the code there is at most a
one-line pointer, `# DEBT: <slug>`.

An entry stays here until the proper fix lands. The change that lands the
fix deletes the entry and its pointers.

## Format

```
### <slug>

- **Where:** `path/to/file.py:function` (and every other site)
- **What it does now:** one or two sentences, present tense.
- **The proper fix:** what doing it right would take.
- **Cost while it stays:** what breaks, misleads or slows down because of it.
```

## Entries

None yet. The comment audit moves the shortcuts now explained inside source
and test files to here.
