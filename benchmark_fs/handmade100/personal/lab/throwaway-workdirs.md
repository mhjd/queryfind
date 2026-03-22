Temporary files
            tmpdir=$(mktemp -d)
            trap 'rm -rf "$tmpdir"' EXIT
            This keeps scratch directories from piling up.
