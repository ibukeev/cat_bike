# Archive retirement record — 2026-09-10

The user authorized permanent deletion of _archive_admin/ and .cleanup-recovery/.

Current status: _archive_admin/ was permanently deleted (946 files,
5,399,146,082 regular-file bytes). Retained worktree hashes were verified before
and after deletion. The rejected generated outputs are no longer recoverable
from this working tree; existing tracked source history and its archive branch remain.

.cleanup-recovery/ was then permanently deleted after the user explicitly
approved the GitHub destination and payload and the independent download passed.
Both archive roots are absent: 956 files removed, 7,474,979,380 regular-file bytes
and 7,478,525,952 allocated bytes (about 6.97 GiB). Local Git/LFS storage remains.

## Verified retained-file backup

- Repository/branch: ibukeev/cat_bike, main.
- Initial checkpoint: 8a49229b7fe511f7f276a3dd46bb32a0622efb8a.
- Verified backup: bd84d8449205c2828a92f32adfedc204fe48b4f8, including the
  LFS attribute correction for four compact OBJ templates stored in ordinary Git.
- A fresh network clone plus Git LFS pull reproduced all 952 tracked files/links
  byte-for-byte, including 209 CAD/print paths / 187 unique LFS objects and all
  167 selected large-head geometry files.
- Git LFS fsck passed. The 17 focused Python tests and mapper/all 10 lighting
  patterns also passed inside that independent checkout.
- The exact 10-file recovery inventory and retained-file preservation checks
  passed before deletion; retained files were checked again afterward.

The backup contains retained work, not either deleted archive payload. Previously
untracked historical tests remain local and were not silently published. Existing
Git history was not rewritten. The broad historical test suite has its recorded
pre-existing failures and is not claimed to pass.

The three original cleanup manifests and the rejected-output checkpoint are
preserved here byte-for-byte for provenance. They describe historical snapshots;
their whole-repository verification commands are obsolete after archive retirement.
Inventories and hashes do not contain the deleted geometry and cannot restore it.

Current build entry points remain in the repository README and retained fabrication
packages. No CAD geometry, design dimensions, approval or generation pins changed.
The separate Git archive branch and existing Git history are not being deleted.

The adjacent archive-retirement.json records the exact deletion targets, preserved
file hashes, verified backup scope and completed permanent deletion of both archives.
