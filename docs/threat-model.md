# Threat Model and Security Limits

## Protected Assets

The tool protects these assets:

- exact source and lock identity
- configured target boundaries
- unmanaged target content
- manager-owned links and records
- honest verification evidence

One invocation gets authority from its five validated configuration files and exact lock.

An authority cannot grant a skill outside its pool. It also cannot implicitly change another authority configuration.

## Fail-Closed Checks

V1 rejects these conditions:

- malformed configuration, duplicate YAML keys, and unknown fields
- malformed manager records
- source, cache, target, transaction, or receipt path escapes
- broken or escaping source links
- unsupported source special files
- mismatched source sets, source types, paths, commits, tree hashes, or skill hashes
- invalid canonical IDs or runtime names
- duplicate runtime names and target path collisions
- grants outside the pool or exact lock
- broken, missing, escaping, or ambiguously owned managed links
- collisions with unmanaged content
- stale plans and target identity changes
- concurrent mutation through cooperating `skillctl` processes
- unsafe receipt or lock publication

Mutation uses lexical path checks and descriptor-relative file operations.

It also uses retained descriptors, inode checks, stable `fcntl` locks, source hashing, staging, backups, journals, and explicit commit boundaries.

Verification hashes the complete cached snapshot. A change to ungranted content also invalidates the evidence.

A REMOVE can affect only strict manager-owned state. The CLI also requires explicit confirmation.

## Trusted Components

The authority owner must trust selected source content. The tool records exact content but does not decide whether instructions are safe.

YAML and frontmatter parsing do not execute code. Git runs without a shell, and terminal prompts are disabled.

The trusted computing base includes these components:

- the local operating system kernel
- filesystem operations
- the Python runtime
- the Git executable
- the operating-system user account

Cooperating callers use `skillctl` locks.

A process with the same or stronger operating-system privileges can still change files, descriptors, process state, or binaries.

## Non-Goals

This tool is not any of these systems:

- a chroot or container
- a mandatory access-control policy
- a capability sandbox
- a malware or secret scanner
- a signature or transparency system
- a defense against root access
- a remote deployment service
- a runtime supervisor
- an automatic Git service

The tool does not authenticate a remote Git server. It records the exact identity that Git returns.

Unmanaged preservation means that the reconciler does not intentionally erase entries without valid manager ownership.

It does not prevent unmanaged content from racing with the process or affecting a downstream consumer.

## Verification Limits

Tests cover specified races and failure boundaries. They cannot cover every kernel or filesystem interleaving.

A multi-target apply provides rollback-oriented process behavior. It is not one atomic operation across filesystems.

Power loss and unusual filesystem durability behavior are not fully proven.

`fsync`, `flock`, inode, hard-link, atomic replacement, and `/proc` behavior can differ by operating system and filesystem.

The release is verified on Linux. V1 does not claim support for macOS, Windows, or network filesystems.

The tool detects content drift when it hashes evidence. It cannot freeze hostile processes outside its lock protocol.

A receipt records a repository commit only when clean tracked configuration bytes bind to that commit. Otherwise, the receipt reports that the commit is unavailable.

A converged receipt proves the checked state at verification time. It does not prove future state or the semantic safety of skill instructions.

## Operator Guidance

Run the tool with the least required privilege.

Use dedicated target roots when possible. Review lock changes and every plan before `apply`.

Store receipts outside the managed host if you need independent evidence.

Keep Git commits and runtime restarts under separate human control.
