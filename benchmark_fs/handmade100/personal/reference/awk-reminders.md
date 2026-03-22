Awk reminders
            awk -F, '{sum += $3} END {print sum}'
            Still easier than spinning up Python for tiny column work.
