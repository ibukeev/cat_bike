#!/usr/bin/env bash
set -euo pipefail

package_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_dir="$package_root/output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-production-owner-review-v8"
production_dir="$package_root/production/eye-modules-v8/right"

mkdir -p "$production_dir"
install -m 0644 \
  "$source_dir/right_eye_bucket_production_owner_v8.step" \
  "$production_dir/right_eye_bucket_production_owner_v8.step"
install -m 0644 \
  "$source_dir/right_eye_rear_cap_production_owner_v8.step" \
  "$production_dir/right_eye_rear_cap_production_owner_v8.step"

(
  cd "$production_dir"
  sha256sum \
    right_eye_bucket_production_owner_v8.step \
    right_eye_rear_cap_production_owner_v8.step \
    > SHA256SUMS
)

echo "Promoted approved right-eye V8 STEP owners to:"
echo "$production_dir"
echo "No STL, G-code, slicer project, left mirror, or print release was created."
