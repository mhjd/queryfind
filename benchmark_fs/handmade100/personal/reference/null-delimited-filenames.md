Filename safety
            Prefer:
            find . -type f -print0 | xargs -0 ls -l
            and when reading lines:
            while IFS= read -r line; do
              printf '%s
' "$line"
            done
