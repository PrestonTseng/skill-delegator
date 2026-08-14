# Threat model and security limits

## Assets and authority

The protected assets are exact source/lock identity, configured target boundaries, unmanaged target content, manager-owned symlinks/metadata, and honest verification evidence. Authority comes only from one invocation's five validated configuration files and exact lock. One authority cannot delegate beyond its pool or implicitly modify another authority domain.

## Fail-closed defenses

V1 rejects, among other cases:

- malformed/duplicate-key/unknown-field configuration and manager metadata;
- source, cache, target, metadata, transaction, and receipt symlink/non-directory escapes at covered boundaries;
- broken or escaping source links and unsupported source special files;
- mismatched configured/locked source sets, types, prefixes, paths, Git commits, complete snapshot tree hashes, and skill hashes;
- hostile canonical or runtime names, duplicate runtime identities, path collisions, and grants outside the pool;
- broken, missing, wrong-destination, escaping, or ambiguously owned managed links;
- unmanaged collisions, stale plans, target/namespace identity replacement, and cooperating concurrent mutation applies;
- receipt overwrite/collision and unsafe lock-publication outcomes.

Mutation uses lexical checks plus descriptor-relative operations, retained directory descriptors/inode identities, stable-order `fcntl` locks, source re-hashing, staging, backups, journals, and explicit commit boundaries. Verification freshly hashes the full cached snapshot exactly once per source, so ungranted additions or changes invalidate evidence. REMOVE is limited to strict manager-owned state and requires CLI confirmation.

## Trusted and untrusted components

Operators must trust the selected source content enough to delegate it; this tool inventories and hashes skill files but does not decide whether their instructions are safe. YAML and frontmatter are parsed without code execution. Git is invoked without a shell and with terminal prompting disabled.

The local OS kernel, filesystem primitives, Python runtime, Git executable, and user account are in the trusted computing base. Cooperative callers use `skillctl` locking. A process with the same or stronger OS privileges can still mutate files, descriptors, process state, or binaries.

## Explicit non-goals

This is not a chroot, container, MAC policy, capability sandbox, malware scanner, signature/transparency system, secret scanner, or defense against root. It does not prevent an authorized local user from editing configured roots. It does not authenticate remote Git servers or establish source provenance beyond the recorded exact identity/hash. It does not provide remote deployment, runtime restart, or automatic Git operations.

Unmanaged preservation means the reconciler does not intentionally delete entries absent from valid manager ownership records. It is not a claim that unmanaged content cannot race with the process or affect downstream consumers.

## Known CANNOT VERIFY limits

- Deterministic fault injection and subprocess tests cover specified races and boundaries; they cannot exhaust every kernel/filesystem interleaving.
- Multi-target apply provides rollback-oriented process semantics, not one atomic cross-directory/filesystem syscall. Power loss and unusual filesystem durability behavior are not exhaustively proven.
- `fsync`, `flock`, inode, hard-link, atomic-replace, and `/proc` descriptor behavior can vary by filesystem/OS. The release candidate is exercised on Linux; macOS/Windows/network filesystems are CANNOT VERIFY for V1.
- The tool detects content drift when it verifies/hashes; it cannot freeze hostile source or target processes outside its descriptor/lock protocol.
- Receipt repository commit evidence is available only when exact tracked config bytes can be bound to the containing clean Git commit. Otherwise the receipt says unavailable; it does not guess.
- A converged receipt proves the checked state at verification time, not future state or semantic safety of skill instructions.

Run under least privilege, keep target roots dedicated where practical, review lock/plan diffs, retain receipts externally if needed, and independently control Git commits and runtime restarts.
