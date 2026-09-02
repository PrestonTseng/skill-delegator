# Descriptor-Bound Directory Entry-Set Rebinding

Use this during closure review of loaders that retain a directory descriptor, discover direct child files, read them descriptor-relatively, and claim the entry set is unchanged afterward.

## Failure mode

Retaining `O_DIRECTORY | O_NOFOLLOW` and opening children with `dir_fd` closes ancestor/pathname substitution, but it does **not** by itself prove a fresh final enumeration.

A loader may:

1. call `os.listdir(directory_fd)` during discovery;
2. read discovered children with `os.open(name, ..., dir_fd=directory_fd)`;
3. call `os.listdir(directory_fd)` again on the same already-enumerated descriptor;
4. compare names and inode identities.

On Linux, the second enumeration can reuse directory-stream state and fail to observe a newly added direct child. Existing-name `lstat` identity checks still catch replacement/removal, while an added declaration can escape parsing and validation.

## Deterministic probe

Inject creation of a second valid direct entry after the last discovered document is read or while it is parsed, but before the final entry-set comparison. Pair this hostile case with controls for:

- an unchanged regular-file directory;
- replacement of an existing child by a symlink;
- replacement of the directory pathname while the retained descriptor remains open;
- removal or inode replacement of an existing child.

The hostile addition must cause the loader to fail with a directory/filename-bearing entry-set-change error. Also print or assert both:

- returned model IDs; and
- actual byte-sorted on-disk entry names.

This prevents a green loader result from hiding an omitted declaration.

## Robust rebinding shape

Obtain a **fresh enumeration handle bound to the retained directory identity** for each list operation. One practical design is to open `.` descriptor-relatively from the retained directory descriptor with no-follow/directory flags, enumerate that fresh FD, and close it. Then:

1. sort names with the contract's byte-order rule;
2. `lstat` each direct name relative to that fresh enumeration descriptor;
3. reject symlinks and non-regular entries;
4. compare the complete final name tuple with discovery;
5. compare `(st_dev, st_ino, file type)` identity for every discovered name.

The file-type component should use the platform's file-type mask (for example, `stat.S_IFMT(st_mode)`), not the full mode: permission changes are not entry replacement, while regular-file-to-directory/device substitution must be detected. Keep the mutation hook one-shot and place it immediately after the original verified read returns so the regression deterministically proves the read-to-rebind gap rather than an unrelated discovery race.

Do not repair a stale-list problem by falling back to the mutable pathname; that reopens the ancestor-replacement race the retained descriptor was meant to close. If using seek/rewind instead, prove portability and fresh-addition visibility on every supported platform.

## Review rule

Treat these as separate closure claims:

- retained directory identity;
- no-follow nested child reads;
- opened-child identity;
- complete final entry-set rebinding.

A passing directory-path replacement test proves only the first two. It does not prove additions are detected. A focused closure review must adversarially exercise each claim independently, even when the full suite passes.
