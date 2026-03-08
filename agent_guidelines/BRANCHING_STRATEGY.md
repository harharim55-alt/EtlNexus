# Git Branching Strategy for Turing v2

This document outlines the Git branching strategy used for the TrekBase project. We will follow a model similar to GitFlow.

## Main Branches

These branches have an infinite lifetime:

- `main`:

  - This branch represents the latest production-ready state of the code.
  - It should only contain tagged releases.
  - Direct commits to `main` are prohibited. Merges to `main` should only come from `release/*` branches or `hotfix/*` branches.
  - Each commit on `main` should be tagged with a version number (e.g., `v0.1.0`, `v1.0.0`).

- `develop`:
  - This is the primary integration branch for ongoing development. All new features and non-hotfix bug fixes are merged into this branch.
  - Nightly builds or continuous integration tests should run against this branch.
  - When `develop` reaches a stable point and is ready for a release, a `release/*` branch is created from it.

## Supporting Branches

These branches have a limited lifetime and are eventually removed:

- `feature/<feature-name>` (e.g., `feature/polygon-connector`, `feature/basic-rsi-calculation`):

  - Used for developing new features.
  - Branched from: `develop`.
  - Must PR, review and approve and merge back into: `develop`.
  - Naming convention: `feature/` followed by a short, descriptive name of the feature (use hyphens for spaces).
  - Should be deleted after merging into `develop`.

- `release/<version-number>` (e.g., `release/v0.1.0`):

  - Used for preparing a new production release.
  - Branched from: `develop` (when `develop` is feature-complete for the release).
  - Tasks on this branch include final testing, bug fixing specific to the release, and updating documentation/version numbers. No new features should be added here.
  - Must PR, review and approve and merge back into: `main` (and be tagged) AND `develop` (to ensure fixes made in the release branch are incorporated back into ongoing development).
  - Should be deleted after merging to `main` and `develop`.

- `hotfix/<issue-description>` (e.g., `hotfix/critical-login-bug`, `hotfix/black-squares-fix`):
  - Used for addressing critical bugs in a production release.
  - Branched from: `main` (from the specific tagged version that has the bug).
  - Must PR, review and approve and merge back into: `main` (and be tagged with a new patch version) AND `develop` (to ensure the fix is incorporated into ongoing development).
  - Should be deleted after merging to `main` and `develop`.

## Workflow Summary

1.  **New Feature Development:**

    - Create `feature/my-feature` from `develop`.
    - Work on the feature.
    - Once complete, merge `feature/my-feature` back into `develop`.
    - Delete `feature/my-feature`.

2.  **Release Preparation:**

    - When `develop` is ready for release, create `release/vX.Y.Z` from `develop`.
    - Perform final tests and bug fixes on the `release` branch.
    - Once ready, merge `release/vX.Y.Z` into `main` and tag the commit on `main` with `vX.Y.Z`.
    - Merge `release/vX.Y.Z` back into `develop`.
    - Delete `release/vX.Y.Z`.

3.  **Hotfix for Production Bug:**
    - Create `hotfix/my-fix` from `main` (from the relevant tag).
    - Fix the bug.
    - Merge `hotfix/my-fix` into `main` and tag with a new patch version (e.g., `vX.Y.Z+1`).
    - Merge `hotfix/my-fix` into `develop`.
    - Delete `hotfix/my-fix`.

This strategy provides a clear separation of concerns for different types of development work and ensures a stable `main` branch representing production code.
