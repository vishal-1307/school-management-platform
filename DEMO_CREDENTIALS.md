# Demo Login Credentials

⚠️ **This is demo data for evaluating the platform — not real school data.** Passwords are intentionally simple and printed in plain text. **Wipe this data (see below) before entering any real student, staff, or fee information.**

This file and `STUDENT_CREDENTIALS.csv` (repo root, all 300 students) are **generated** by `backend/app/scripts/seed_prod.py` — re-run it to regenerate. Every login uses the institutional ID + password scheme.

**Boot vs. manual**: only the bootstrap layer (school profile, academic year, classes/sections, subjects, fee structures, the `admin` login) runs automatically on every backend boot via `SEED_ON_START`. The full dataset below — teachers, 300 students, attendance, exams, fees, homework, notices, timetable, admissions, contact messages — does **not** run on boot. Run it once, manually: `python -m app.scripts.seed_prod` (from `backend/`), pointed at the target database.

## Admin

| Login ID | Password |
|---|---|
| `admin` | `Admin@2026` |

## Teachers (all, including floating/substitute)

| Login ID | Name | Designation | Subjects |
|---|---|---|---|
| `EMP-001` | Siddharth Banerjee | Pre-Primary Teacher | PED101, RHY101 |
| `EMP-002` | Zara Bansal | Pre-Primary Teacher | ART101, RHY101 |
| `EMP-003` | Karthik Chopra | Pre-Primary Teacher | ART101, NUM101 |
| `EMP-004` | Vihaan Menon | Pre-Primary Teacher | LIT101, NUM101 |
| `EMP-005` | Aditi Mishra | PRT | ENG101 |
| `EMP-006` | Pranav Reddy | PRT | HIN101 |
| `EMP-007` | Diya Mukherjee | PRT | MAT101 |
| `EMP-008` | Lavanya Malhotra | PRT | EVS101 |
| `EMP-009` | Aniket Kaul | PRT | CSC101 |
| `EMP-010` | Saanvi Kumar | PRT | ART101 |
| `EMP-011` | Avni Chawla | PRT | PED101 |
| `EMP-012` | Rudra Malhotra | TGT | ENG101, PED101 |
| `EMP-013` | Sara Ghosh | TGT | ENG101, HIN101 |
| `EMP-014` | Harsh Chauhan | TGT | HIN101, MAT101 |
| `EMP-015` | Nisha Chawla | TGT | MAT101, SCI101 |
| `EMP-016` | Hiya Chawla | TGT | SCI101, SST101 |
| `EMP-017` | Advait Naidu | TGT | CSC101, SST101 |
| `EMP-018` | Jiya Yadav | TGT | CSC101, GKN101 |
| `EMP-019` | Vanya Sen | PGT | ENG101 |
| `EMP-020` | Zara Hegde | PGT | MAT101 |
| `EMP-021` | Kabir Chawla | PGT | PHY101 |
| `EMP-022` | Pari Kumar | PGT | CHM101 |
| `EMP-023` | Parth Sharma | PGT | BIO101 |
| `EMP-024` | Gauri Das | PGT | ECO101 |
| `EMP-025` | Ishita Reddy | PGT | BST101 |
| `EMP-026` | Veer Nair | PGT | ACC101 |
| `EMP-027` | Atharv Jain | PGT | CSC101 |
| `EMP-028` | Parth Tiwari (floating) | Floating / Substitute Teacher | — |
| `EMP-029` | Atharv Kulkarni (floating) | Floating / Substitute Teacher | — |
| `EMP-030` | Riya Gupta (floating) | Floating / Substitute Teacher | — |
| `EMP-031` | Anika Sen (floating) | Floating / Substitute Teacher | — |

All teacher logins use password `Teach@2026`.

## Students — representative sample

One strong-attendance+fully-paid, one chronic-absentee+defaulter, and one average student per class level. **All 300 students have working logins** — see `STUDENT_CREDENTIALS.csv` at the repo root for the full list.

All student logins use password `Study@2026`.

| Login ID | Name | Class | Attendance | Fees |
|---|---|---|---|---|
| `ADM-00001` | Varun Hegde | Nursery-A | strong | full |
| `ADM-00011` | Reyansh Mehta | Nursery-B | strong | full |
| `ADM-00002` | Meera Kumar | Nursery-A | chronic | defaulter |
| `ADM-00012` | Riya Sen | Nursery-B | chronic | defaulter |
| `ADM-00003` | Kartik Naidu | Nursery-A | average | full |
| `ADM-00021` | Kartik Bhatt | LKG-A | strong | full |
| `ADM-00031` | Aniket Bose | LKG-B | strong | full |
| `ADM-00022` | Aarohi Reddy | LKG-A | chronic | defaulter |
| `ADM-00032` | Tara Pandey | LKG-B | chronic | defaulter |
| `ADM-00023` | Arnav Chawla | LKG-A | average | full |
| `ADM-00041` | Dhruv Bansal | UKG-A | strong | full |
| `ADM-00051` | Arnav Bhatt | UKG-B | strong | full |
| `ADM-00042` | Lavanya Reddy | UKG-A | chronic | defaulter |
| `ADM-00052` | Trisha Sen | UKG-B | chronic | defaulter |
| `ADM-00043` | Ayaan Mukherjee | UKG-A | average | full |
| `ADM-00061` | Aarav Menon | Class 1-A | strong | full |
| `ADM-00071` | Aarav Kumar | Class 1-B | strong | full |
| `ADM-00062` | Sara Kaul | Class 1-A | chronic | defaulter |
| `ADM-00072` | Avni Das | Class 1-B | chronic | defaulter |
| `ADM-00063` | Arnav Das | Class 1-A | average | full |
| `ADM-00081` | Reyansh Bose | Class 2-A | strong | full |
| `ADM-00091` | Arnav Iyer | Class 2-B | strong | full |
| `ADM-00082` | Kavya Yadav | Class 2-A | chronic | defaulter |
| `ADM-00092` | Avni Kumar | Class 2-B | chronic | defaulter |
| `ADM-00083` | Aryan Patel | Class 2-A | average | full |
| `ADM-00101` | Aarav Bansal | Class 3-A | strong | full |
| `ADM-00111` | Shaurya Singh | Class 3-B | strong | full |
| `ADM-00102` | Aadhya Chauhan | Class 3-A | chronic | defaulter |
| `ADM-00112` | Khushi Kumar | Class 3-B | chronic | defaulter |
| `ADM-00103` | Rishi Singh | Class 3-A | average | full |
| `ADM-00121` | Siddharth Bhatt | Class 4-A | strong | full |
| `ADM-00131` | Kabir Kumar | Class 4-B | strong | full |
| `ADM-00122` | Kavya Kumar | Class 4-A | chronic | defaulter |
| `ADM-00132` | Ananya Naidu | Class 4-B | chronic | defaulter |
| `ADM-00123` | Parth Hegde | Class 4-A | average | partial |
| `ADM-00141` | Karthik Pandey | Class 5-A | strong | full |
| `ADM-00151` | Yuvraj Chopra | Class 5-B | strong | full |
| `ADM-00142` | Pari Khan | Class 5-A | chronic | defaulter |
| `ADM-00152` | Ishita Tiwari | Class 5-B | chronic | defaulter |
| `ADM-00143` | Kabir Das | Class 5-A | average | full |
| `ADM-00161` | Pranav Chawla | Class 6-A | strong | full |
| `ADM-00171` | Atharv Patel | Class 6-B | strong | full |
| `ADM-00162` | Bhavya Das | Class 6-A | chronic | defaulter |
| `ADM-00172` | Diya Menon | Class 6-B | chronic | defaulter |
| `ADM-00163` | Nikhil Gupta | Class 6-A | average | unpaid |
| `ADM-00181` | Veer Nair | Class 7-A | strong | full |
| `ADM-00191` | Rudra Gupta | Class 7-B | strong | full |
| `ADM-00182` | Zara Kaul | Class 7-A | chronic | defaulter |
| `ADM-00192` | Anika Bansal | Class 7-B | chronic | defaulter |
| `ADM-00183` | Krishna Rao | Class 7-A | average | partial |
| `ADM-00201` | Dhruv Verma | Class 8-A | strong | full |
| `ADM-00211` | Nikhil Kaul | Class 8-B | strong | full |
| `ADM-00202` | Sara Malhotra | Class 8-A | chronic | defaulter |
| `ADM-00212` | Disha Pandey | Class 8-B | chronic | defaulter |
| `ADM-00203` | Arjun Malhotra | Class 8-A | average | full |
| `ADM-00221` | Arnav Bose | Class 9-A | strong | full |
| `ADM-00231` | Rishi Pandey | Class 9-B | strong | full |
| `ADM-00222` | Avni Gupta | Class 9-A | chronic | defaulter |
| `ADM-00232` | Zara Chauhan | Class 9-B | chronic | defaulter |
| `ADM-00223` | Tanish Verma | Class 9-A | average | partial |
| `ADM-00241` | Yash Nair | Class 10-A | strong | full |
| `ADM-00251` | Advait Verma | Class 10-B | strong | full |
| `ADM-00242` | Charvi Bhatt | Class 10-A | chronic | defaulter |
| `ADM-00252` | Pari Banerjee | Class 10-B | chronic | defaulter |
| `ADM-00243` | Varun Gupta | Class 10-A | average | unpaid |
| `ADM-00261` | Kartik Kapoor | Class 11-A | strong | full |
| `ADM-00271` | Naman Verma | Class 11-B | strong | full |
| `ADM-00262` | Ira Patel | Class 11-A | chronic | defaulter |
| `ADM-00272` | Anika Mishra | Class 11-B | chronic | defaulter |
| `ADM-00263` | Yash Bhatt | Class 11-A | average | full |
| `ADM-00281` | Veer Tiwari | Class 12-A | strong | full |
| `ADM-00291` | Ayaan Menon | Class 12-B | strong | full |
| `ADM-00282` | Zara Yadav | Class 12-A | chronic | defaulter |
| `ADM-00292` | Gauri Pillai | Class 12-B | chronic | defaulter |
| `ADM-00283` | Yash Jain | Class 12-A | average | full |

**Parents:** no separate parent login — parents sign in with their child's student ID and password exactly as a student would.

## Wiping the demo data before real data goes in

Run this **from your own machine**, pointed at the production database:

```bash
cd backend
echo 'DATABASE_URL=<paste the production Neon URL here>' >> .env
python -m app.scripts.reset_demo --yes
```

This deletes every data row but keeps the schema, then re-creates only the bootstrap layer (school profile, academic year, classes/sections, subjects, fee structures) and a single `admin` login with a password you choose interactively. No demo teachers/students/attendance are recreated. Afterward, also set `SEED_ON_START=false` on Render.
