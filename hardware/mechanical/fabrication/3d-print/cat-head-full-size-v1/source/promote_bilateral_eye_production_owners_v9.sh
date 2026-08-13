#!/usr/bin/env bash
set -euo pipefail

package_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
right_source_dir="$package_root/production/eye-modules-v8/right"
left_source_dir="$package_root/output/70-freecad-pilots/opposite-side-flange-pilot-v1/eye-bilateral-exact-mirror-review-v9"
production_root="$package_root/production/eye-modules-v9"
right_dir="$production_root/right"
left_dir="$production_root/left"

mkdir -p "$right_dir" "$left_dir"

# The right owners are byte-identical copies of the user-approved V8 inputs.
install -m 0644 \
  "$right_source_dir/right_eye_bucket_production_owner_v8.step" \
  "$right_dir/right_eye_bucket_production_owner_v9.step"
install -m 0644 \
  "$right_source_dir/right_eye_rear_cap_production_owner_v8.step" \
  "$right_dir/right_eye_rear_cap_production_owner_v9.step"

# The left owners are the exact X=0 mirrors reviewed and approved in V9.
install -m 0644 \
  "$left_source_dir/left_eye_bucket_exact_x0_mirror_v9.step" \
  "$left_dir/left_eye_bucket_production_owner_v9.step"
install -m 0644 \
  "$left_source_dir/left_eye_rear_cap_exact_x0_mirror_v9.step" \
  "$left_dir/left_eye_rear_cap_production_owner_v9.step"

(
  cd "$production_root"
  sha256sum \
    right/right_eye_bucket_production_owner_v9.step \
    right/right_eye_rear_cap_production_owner_v9.step \
    left/left_eye_bucket_production_owner_v9.step \
    left/left_eye_rear_cap_production_owner_v9.step \
    > SHA256SUMS
)

echo "Promoted user-approved bilateral-eye V9 STEP owners to:"
echo "$production_root"
echo "No STL, G-code, slicer project, flange union, or print release was created."
