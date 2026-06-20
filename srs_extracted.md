SOFTWARE REQUIREMENTS SPECIFICATION

School Website & Management Platform

A complete specification of the public website, the Admin / Teacher / Student portals, parent communication, and all role-based features to be built.

Field

Detail

Prepared for

[ SCHOOL NAME ]

Prepared by

Vishal Kumar Thakur

Document type

Software Requirements Specification (SRS)

Version

1.0 — Draft for Review

Status

Pending client (school) sign-off

How to use this document: This SRS describes exactly what will be built — every page, every screen, and every control each user type (Admin, Teacher, Student, Parent) will have. Review it section by section with the school and mark anything to add, remove, or change before development begins.

Table of Contents

Table of Contents2

1. Introduction4

1.1 Purpose4

1.2 Scope4

1.3 Intended Audience4

1.4 Out of Scope (Phase 1)4

2. Overall System Description5

2.1 Product Perspective5

2.2 User Classes and Characteristics5

2.3 Recommended Technology Stack5

2.4 Assumptions and Constraints5

3. System Architecture Overview7

4. Public Website — Sitemap & Page Specifications8

4.1 Sitemap (all public pages)8

4.2 Page-by-Page Specification8

5. User Roles & Authentication11

5.1 Role List11

5.2 Login & Authentication Requirements11

6. Admin Portal — Page-by-Page Specification12

7. Teacher Portal — Page-by-Page Specification16

8. Student Portal — Page-by-Page Specification18

9. Parent Access — WhatsApp & Optional Login20

9.1 WhatsApp Updates (Primary Channel)20

9.2 Optional Parent Web Login20

10. Role-Based Permission Matrix21

11. Functional Requirements22

11.1 Authentication & Access Control22

11.2 Student & Staff Management22

11.3 Attendance22

11.4 Fee Management22

11.5 Examinations & Results22

11.6 Homework & Timetable22

11.7 Notices & Communication22

11.8 Website Content Management22

12. Non-Functional Requirements24

12.1 Performance24

12.2 Security24

12.3 Availability & Reliability24

12.4 Usability24

12.5 Compliance24

12.6 Scalability24

13. High-Level Data Entities25

14. Third-Party Integrations26

15. Future Scope — AI & Automation Add-Ons27

16. Glossary28

Note: Open this document in Microsoft Word, click inside the Table of Contents, and press F9 (or right-click → Update Field) to populate page numbers.

1. Introduction

1.1 Purpose

This document specifies the complete functional and non-functional requirements for the [ SCHOOL NAME ] digital platform — a public school website combined with a role-based management system used by the School Admin, Teachers, and Students, with parent communication handled primarily through WhatsApp. It is the single reference both the school and the developer will use to agree on scope before any design or coding begins.

1.2 Scope

The platform covers two connected parts:

Public Website — the school's online face: information for parents, prospective families, and visitors. No login required.

Management Portals — secure, role-based areas for the Admin (owner/principal), Teachers, and Students, covering attendance, fees, exams, homework, timetable, and communication.

Parent-facing communication (attendance alerts, fee reminders, results, notices) is delivered primarily over WhatsApp, with an optional lightweight Parent web view for those who want to log in directly. AI-based automation (call assistant, auto-replies, content generation) is listed under Future Scope (Section 16) and is priced and scheduled separately from the core build.

1.3 Intended Audience

School management / owner — to review and approve what is being built

Teachers and office staff — to understand what tools they will get

Developer (Vishal Kumar Thakur) — as the build blueprint

1.4 Out of Scope (Phase 1)

The following are intentionally excluded from the first build and can be added later as paid add-ons: hostel management, library circulation system, transport GPS tracking, payroll/HR, and AI-based automation. These are listed for completeness in Section 16.

2. Overall System Description

2.1 Product Perspective

The platform is a single connected system with one shared database. Content entered once by the Admin (a notice, a gallery photo, an achievement) automatically reflects on the public website — the school never edits the same information twice. The system is structured as four user-facing surfaces:

Surface

Who uses it

Login required

Public Website

Parents, prospective families, the general public

No

Admin Portal

School owner / Principal / Office staff

Yes

Teacher Portal

Teaching staff

Yes

Student Portal

Enrolled students

Yes

Parent Access

Parents / guardians

Primarily WhatsApp; optional light login

2.2 User Classes and Characteristics

Super Admin (Owner/Principal) — full control over every module and every other user's access.

Office Admin Staff (optional sub-role) — day-to-day data entry under the Super Admin, with permissions the Super Admin chooses to grant.

Teacher — access limited to their own assigned classes and subjects.

Student — read-mostly access to their own academic record.

Parent — receives updates and can pay fees; no editing rights anywhere.

Visitor — anonymous public website visitor; no login.

2.3 Recommended Technology Stack

This reuses the same production-proven architecture already running on the developer's other live platforms, which keeps cost and delivery time down:

Layer

Technology

Public website

Astro 5 + React islands + Tailwind CSS — fast-loading, mobile-first, SEO-friendly

Management portals

React, role-protected routes

Backend API

FastAPI (Python)

Database

PostgreSQL (managed, e.g. Neon)

Authentication

Clerk — role-based login for Admin / Teacher / Student

Media storage

Cloudinary — photos, gallery, documents

Payments

Razorpay — online fee collection

Parent communication

WhatsApp Business Cloud API

Hosting

Vercel (frontend) + DigitalOcean / Railway (backend)

2.4 Assumptions and Constraints

The school will provide existing student/staff data (Excel sheets or registers) for one-time migration.

The school will provide a logo, photographs, and text content (About Us, achievements, etc.); placeholder content is used until then.

One nominated person at the school (Owner/Principal) will act as the Super Admin and approve access for others.

Internet connectivity at the school office is assumed sufficient for browser-based daily use.

Pricing, payment terms, and timeline are covered in the separate Proposal document, not in this SRS.

3. System Architecture Overview

At a high level, data flows in one direction from entry to every surface that needs it:

Step

Flow

1

Admin / Teacher enters data (student record, attendance, marks, notice, gallery photo) into the portal.

2

Data is saved once in the central database.

3

Relevant parts automatically appear on: the public website (if public-facing), the Student Portal (if relevant to the student), and a WhatsApp message to the Parent (if it's an alert-type event such as attendance, fee due, or result).

4

Reports and dashboards read from the same database in real time — no manual reconciliation.

Security model: every API request is checked against the logged-in user's role before any data is returned or changed — a Teacher's request for fee data, for example, is rejected by the backend itself, not just hidden in the interface.

4. Public Website — Sitemap & Page Specifications

4.1 Sitemap (all public pages)

1. Home

2. About Us

3. Academics

4. Admissions

5. Faculty

6. Facilities

7. Gallery

8. Achievements & News

9. Mandatory Public Disclosure (CBSE compliance)

10. Notices / Circulars

11. Contact Us

12. Portal Login (gateway to Admin / Teacher / Student login)

4.2 Page-by-Page Specification

4.2.1  Home Page

Purpose: First impression — quick orientation for any visitor in under 10 seconds.

Header with school logo, name, and main navigation menu

Hero banner / image slider showcasing the campus, students, and key achievements

Quick-access buttons: Admissions Enquiry, Results, Notices, Contact

Welcome message from the Principal / Director (photo + short text)

“Why Choose Us” strip — years of operation, student strength, board affiliation, key facilities (as short stat cards)

Scrolling/latest notices ticker pulling live from the Notices module

Upcoming events preview (next 2–3 events)

Prominent “Mandatory Public Disclosure” icon/button (CBSE compliance requirement — must be visible on the home page)

Parent / student testimonials (optional, rotating)

Footer: address, phone, email, social media links, quick links, map snippet

4.2.2  About Us

Purpose: Builds trust — history, leadership, and credibility.

School history and founding story

Vision, mission and core values

Message from Management / Trustees and from the Principal

Infrastructure and campus overview (with photos)

Affiliation details — board name, affiliation number, recognition certificates

4.2.3  Academics

Purpose: Explains what and how the school teaches.

Curriculum/board overview (e.g. CBSE / State Board) and classes offered (Pre-Primary to Class XII as applicable)

Class-wise structure: Pre-Primary, Primary, Middle, Secondary, Senior Secondary — streams offered at senior level

Subjects offered per level

Examination pattern and academic calendar (downloadable PDF)

Teaching methodology highlights (smart classes, activity-based learning, etc.)

4.2.4  Admissions

Purpose: The page most likely to convert a visit into an enquiry — the most important page on the site.

Admission process steps and eligibility / age criteria per class

Online Admission Enquiry Form: Child’s name, date of birth, class applying for, parent name, phone, email, address, how they heard about the school, message — submissions flow directly into the Admin’s Enquiry Management list (Section 6.4) and trigger the automatic WhatsApp follow-up, if enabled

Required documents checklist (birth certificate, transfer certificate, previous report card, photos, etc.)

Fee structure (or “contact school for fee details” if the school prefers not to publish fees)

Important admission dates / calendar

4.2.5  Faculty

Purpose: Shows parents the quality and experience of the teaching staff.

Faculty directory grouped by department/level: photo, name, subject taught, qualification (only for staff who consent to being listed)

Principal / Vice-Principal profile

4.2.6  Facilities

Purpose: Demonstrates the school is well-equipped and modern.

Library, Science Lab(s), Computer Lab, Smart Classrooms

Sports facilities and playground

Transport (if applicable)

Medical room / first-aid, cafeteria, hostel (if applicable)

Each facility shown with a short description and photo

4.2.7  Gallery

Purpose: Visual proof of school life — strongly influences a parent’s decision.

Photo gallery organised into event-wise albums (Annual Day, Sports Day, Independence Day, classroom activities, etc.)

Video gallery (YouTube/Vimeo embeds)

Admin can create a new album and upload photos directly from the Admin Portal — no developer needed

4.2.8  Achievements & News

Purpose: Builds pride and social proof.

Student achievements (academic, sports, competitions — e.g. Codeavour, Olympiads)

School-level achievements and awards

News updates and an events calendar with upcoming dates

4.2.9  Mandatory Public Disclosure

Purpose: Required compliance page for CBSE-affiliated schools (CBSE Affiliation Bye-Laws, Clause 2.4.9) — also signals to parents that the school is properly recognised and transparent.

General information: affiliation number, school code, address, principal’s qualification, year of establishment

Documents and information as per the CBSE-prescribed format: building safety certificate, fire safety certificate, recognition certificate, society/trust registration, list of school management committee members, etc.

This page must be linked from a clearly visible icon on the Home Page at all times

4.2.10  Notices / Circulars (Public Board)

Purpose: A public, always-current notice board — reduces “when does school reopen” phone calls.

Chronological list of notices marked “public” by the Admin (holidays, exam dates, general announcements)

Downloadable PDF circulars where applicable

Same notices are also pushed to parents on WhatsApp automatically

4.2.11  Contact Us

Purpose: Makes it effortless to reach the school.

Address with embedded Google Map

Phone number(s), email, office hours

Contact form (name, email/phone, message) — submissions go to the Admin’s inbox/dashboard

Click-to-chat WhatsApp button

4.2.12  Portal Login (Gateway)

Purpose: Single, clearly labelled entry point so the right person reaches the right login.

Three clearly separated buttons: Admin Login, Teacher Login, Student Login

Each leads to its own secure sign-in screen (Section 5.2)

5. User Roles & Authentication

5.1 Role List

Role

Description

Super Admin

The school owner / principal. Full access to every module described in Section 6.

Office Admin Staff (optional)

Created by the Super Admin with a chosen subset of permissions — e.g. only Admissions + Fees.

Teacher

Access scoped to the classes and subjects assigned to them by the Admin.

Student

Access scoped to their own academic record only.

Parent

Receives WhatsApp updates; optional read-only web login; can make fee payments.

5.2 Login & Authentication Requirements

Each role has its own login screen (Admin / Teacher / Student), reached from the Portal Login gateway page.

Login via mobile number + OTP, or email + password (school’s choice); Admin can reset any user’s password.

Student and Staff login credentials are auto-generated by the Admin when a record is created, and can be shared via WhatsApp/SMS.

Session expires after a period of inactivity; re-login required for sensitive actions like fee refunds.

All passwords are stored encrypted; the platform never stores plain-text passwords.

6. Admin Portal — Page-by-Page Specification

The Admin Portal is the control centre of the entire platform. The Super Admin has access to every page below; if Office Admin Staff accounts are created, the Super Admin chooses which of these pages each staff account can see.

6.1  Admin Dashboard

Purpose: One-glance health check of the whole school, the moment Admin logs in.

Total students, total staff, today’s attendance % (student & staff)

Fees collected this month vs. dues outstanding (with a defaulter count)

New admission enquiries awaiting follow-up

Recently sent notices and their WhatsApp delivery status

Quick-action buttons: Add Student, Mark Attendance Override, Send Notice, Add Notice to Website

6.2  Student Management

Purpose: The master record for every student in the school.

Add / Edit / Deactivate a student record (photo, name, DOB, class, section, roll number, parent name & phone, address, documents)

Bulk import students from an Excel sheet (for first-time data migration)

Assign / change class and section

Generate Transfer Certificate (TC) / Bonafide Certificate from a template

Promote a whole class to the next academic year in one action

Search and filter by class, section, or name

6.3  Staff Management

Purpose: The master record for every teacher and staff member.

Add / Edit / Deactivate a staff record (photo, name, contact, qualification, subjects, classes assigned)

Assign subjects and classes to each teacher (this directly controls what that teacher can see in their own portal)

Mark / review staff attendance

Create login credentials for new staff and assign their role (Teacher / Office Admin Staff)

6.4  Admissions / Enquiry Management

Purpose: Converts website interest into enrolled students — the school’s growth engine.

List of every enquiry submitted from the website Admissions form, newest first

Status pipeline per enquiry: New → Contacted → Visited → Admitted → Not Interested

Notes field to log call/visit details

One-click “Convert to Student” once admitted, which pre-fills the Student Management form

(With automation enabled) automatic WhatsApp follow-up sequence to enquiries that haven’t responded — see Section 16

6.5  Fee Management

Purpose: The single most-used module — removes register-based fee chaos entirely.

Set up fee structure per class (tuition, transport, exam fee, etc.) and per term/installment

Record offline (cash/cheque) payments and generate GST-ready digital receipts

View online payments collected via Razorpay automatically, with receipt auto-generated

Live defaulter list — who hasn’t paid, how much, since when

Trigger fee due WhatsApp reminders (manual or automatic, see Section 16)

Export fee collection reports (daily / monthly / by class) to Excel

Process refunds with an approval/reason note

6.6  Attendance Management

Purpose: Oversight and correction layer above what teachers mark daily.

View attendance for any class/section/date

Override or correct an attendance entry (with a logged reason)

Staff attendance overview

Class-wise and student-wise attendance percentage reports

List of students below a configurable attendance threshold (e.g. under 75%)

6.7  Exam & Result Management

Purpose: Controls the entire exam-to-report-card pipeline.

Create exam schedules (Unit Test, Half-Yearly, Annual, etc.) per class

Configure subjects, maximum marks, and grading scale per exam

Review marks entered by teachers before publishing

Lock / Unlock result visibility for students and parents (so results only become visible when the school is ready)

Generate and customise the report card template (board-correct format, school logo, grading remarks)

Bulk-generate and download/print report cards for an entire class

6.8  Timetable Management

Purpose: Keeps the whole school’s schedule organised and conflict-free.

Create/edit the weekly timetable per class and section

Assign teacher-to-period mapping (warns on double-booking a teacher)

Assign a substitute teacher when a teacher is on leave, with one click

Publish updated timetable instantly to all affected Teacher and Student portals

6.9  Notice / Circular Management

Purpose: One place to reach the whole school, or just the people who need it.

Compose a notice with title, description, and optional file attachment

Choose audience: Everyone / Specific class / Staff only

Choose channels: Website Notice Board, Student Portal, WhatsApp broadcast to parents

Schedule a notice for a future date/time (e.g. tomorrow’s holiday announcement)

View delivery status of WhatsApp broadcasts (sent / delivered)

6.10  Homework Oversight

Purpose: Lets the Admin see what is being assigned across the school without doing the work themselves.

View all homework posted, filterable by class, subject, or teacher

Spot classes/subjects with no homework activity over a chosen period

6.11  Website Content Manager (CMS)

Purpose: Lets the Admin keep the public website current without ever calling a developer.

Edit Home Page banner images and the “Why Choose Us” stats

Add/remove Gallery albums and photos

Add/edit Achievements and News & Events entries

Add/edit Faculty directory entries

Update the Mandatory Public Disclosure information and documents

Edit Contact details and embedded map

6.12  Reports & Analytics

Purpose: Turns daily data into decisions.

Attendance trend charts (school-wide, class-wise, over time)

Fee collection trend and outstanding-dues trend

Admission enquiry → admission conversion rate

Exam performance summary by class/subject

All reports exportable to Excel/PDF

6.13  Communication Log

Purpose: Full visibility into every automated message sent on the school’s behalf.

Searchable log of every WhatsApp message sent (attendance alerts, fee reminders, notices, results)

Delivery status per message (sent / delivered / failed)

6.14  Automation Settings

Purpose: Switches for every paid automation add-on — see Section 16 for what each one does.

Enable/disable the AI Call Assistant and review its call logs

Configure automatic fee reminder schedule (e.g. 5 days before due, on due date, 3 days after)

Configure automatic admission enquiry follow-up sequence

Configure social media auto-posting schedule

6.15  User & Role Management

Purpose: Controls who can do what inside the system itself.

Create logins for Office Admin Staff and assign exactly which pages/modules they can access

Reset any user’s password

Deactivate a user’s access immediately (e.g. staff who has left)

View a log of which Admin user made which change (audit trail)

6.16  School Settings

Purpose: One-time and occasional setup that affects the whole system.

School profile: name, logo, address, affiliation number, contact details

Academic year / session setup

Class and section setup, subject setup

Holiday calendar setup

7. Teacher Portal — Page-by-Page Specification

A teacher only ever sees the classes and subjects the Admin has assigned to them — never the whole school’s data.

7.1  Teacher Dashboard

Purpose: Everything a teacher needs the moment they log in, before their first period.

Today’s timetable / class schedule

Pending homework to review/grade

Quick-access “Mark Attendance” shortcut for the current period’s class

Latest notices relevant to staff

7.2  My Classes & Timetable

Purpose: Clarity on what and when they teach.

List of assigned classes, sections, and subjects

Personal weekly timetable view

7.3  Attendance

Purpose: Daily attendance marking — the most frequent action a teacher takes in the system.

Mark present/absent/late for each student in the assigned class, per period or per day

Edit the same day’s attendance if a mistake is caught before end of day

View attendance history for their own classes

7.4  Homework / Assignments

Purpose: Posting and tracking classwork.

Post homework with description and optional file attachment, visible instantly in the Student Portal

See submission status per student (if online submission is enabled)

Mark homework as reviewed/complete

7.5  Marks / Gradebook Entry

Purpose: Entering exam results for their own subjects only.

Enter marks for each student, for the subjects and classes assigned to them

Submit marks for Admin review and lock (Section 6.7) — cannot edit after Admin locks the exam

7.6  My Students (View Only)

Purpose: Academic context without access to sensitive data.

View academic and attendance record for students in their own class(es) only

No visibility into fee or other students’ personal/financial information

7.7  Notices

Purpose: Two-way but controlled communication.

View all school notices relevant to staff

Post a class-specific notice, if the Admin has granted this permission

7.8  Leave Application

Purpose: Self-service instead of paper leave forms.

Apply for leave with date range and reason

View approval status and remaining leave balance

7.9  My Profile

Purpose: Basic self-management.

View/update own contact details and profile photo

Change password

8. Student Portal — Page-by-Page Specification

The Student Portal is read-mostly: students can see their own record clearly, but cannot edit academic data.

8.1  Student Dashboard

Purpose: A clear daily snapshot for the student.

Today’s timetable

Current attendance percentage

Pending homework

Latest notices relevant to their class

8.2  My Attendance

Purpose: Transparency into their own record.

Day-wise and monthly attendance history with percentage

8.3  Homework

Purpose: Keeping track of what’s due.

View homework assigned to their class with due dates

Upload a submission file, if the teacher has enabled online submission

8.4  Results / Report Card

Purpose: Exam outcomes, once released by the Admin.

View marks subject-wise once the Admin unlocks the exam result

Download the official report card as a PDF

8.5  My Timetable

Purpose: Always-current class schedule.

Full weekly timetable for their class/section

8.6  Notices

Purpose: Stay informed.

All notices relevant to their class

8.7  Fee Status (View Only)

Purpose: Awareness without giving editing rights.

View fee due / paid history and download receipts

“Pay Now” button linking to the same secure Razorpay payment used by parents

8.8  My Profile

Purpose: Basic self-service.

View own details (name, class, roll number, etc.)

Request a correction (sent to Admin for approval — students cannot self-edit official records)

Change password

9. Parent Access — WhatsApp & Optional Login

Parents are the platform’s most important audience but the least technical — so by design they are not required to download an app or remember a login. WhatsApp is the primary channel; a lightweight optional web view is available for parents who want it.

9.1 WhatsApp Updates (Primary Channel)

Daily attendance alert if the child is marked absent

Fee due reminder with a direct one-tap payment link

Exam results notification the moment the Admin unlocks them

School notices, holidays, and circulars

Reply support for simple queries (with the AI Call/Chat Assistant add-on, see Section 16)

9.2 Optional Parent Web Login

9.2.1  Parent Dashboard

Purpose: A simple, mirrored view of their child’s school life, for parents who prefer a web view over WhatsApp.

Child selector (if more than one child is enrolled at the school)

Attendance summary, latest results, fee status, and notices for the selected child

“Pay Fees” button (Razorpay)

Notification preferences (which WhatsApp alerts to receive)

10. Role-Based Permission Matrix

V = View, A = Add, E = Edit, D = Delete, — = No access. This table is the definitive reference for what each role can and cannot do.

Module / Feature

Admin

Teacher

Student

Parent

Student records

V/A/E/D

View (own class)

View (own)

View (own child)

Staff records

V/A/E/D

—

—

—

Admissions / Enquiries

V/A/E/D

—

—

—

Attendance — mark

V/E (override)

Add/Edit (own class, same day)

—

—

Attendance — view

V

V (own class)

V (own)

V (own child)

Fee structure & collection

V/A/E/D

—

—

—

Fee payment

V (all)

—

Pay (own)

Pay (own child)

Exam setup & locking

V/A/E/D

—

—

—

Marks entry

V/E (review)

Add/Edit (own subject, until locked)

—

—

Results / report card

V/A/E/D

V (own class)

V (own, once unlocked)

V (own child, once unlocked)

Homework

V

Add/Edit (own class)

V (own class) / Submit

V (own child, read-only)

Timetable

V/A/E/D

V (own)

V (own)

V (own child)

Notices

V/A/E/D

Add (class-level, if permitted) / View

V

V

Website content (CMS)

V/A/E/D

—

—

—

Reports & analytics

V

—

—

—

User & role management

V/A/E/D

—

—

—

Automation settings

V/A/E/D

—

—

—

11. Functional Requirements

11.1 Authentication & Access Control

FR-1: The system shall provide separate login screens for Admin, Teacher, and Student.

FR-2: The system shall restrict every API request to actions permitted for that user’s role, regardless of what the interface shows.

FR-3: The Admin shall be able to create, deactivate, and reset credentials for any user.

11.2 Student & Staff Management

FR-4: The Admin shall be able to add, edit, and deactivate student and staff records, including bulk import from Excel.

FR-5: The system shall auto-generate a unique enrollment/admission number for each new student.

FR-6: The Admin shall be able to generate a Transfer Certificate or Bonafide Certificate from a stored template, pre-filled with the student’s record.

11.3 Attendance

FR-7: A Teacher shall be able to mark attendance for their assigned class for the current day only.

FR-8: The Admin shall be able to override any attendance record, with the change logged.

FR-9: The system shall automatically send a WhatsApp alert to the parent when a student is marked absent.

11.4 Fee Management

FR-10: The Admin shall be able to define a fee structure per class and per term.

FR-11: The system shall generate a digital, GST-ready receipt automatically for every payment, online or offline.

FR-12: The system shall reconcile online Razorpay payments to the correct student automatically.

FR-13: The system shall maintain a real-time defaulter list.

11.5 Examinations & Results

FR-14: A Teacher shall be able to enter marks only for subjects and classes assigned to them.

FR-15: The Admin shall be able to lock an exam so no further mark edits are possible without unlocking it.

FR-16: Results shall remain invisible to Students and Parents until the Admin explicitly unlocks them.

FR-17: The system shall generate a board-correct report card as a downloadable PDF.

11.6 Homework & Timetable

FR-18: A Teacher shall be able to post homework visible immediately to their assigned class’s Student Portal.

FR-19: The Admin shall be able to build and publish a weekly timetable per class, with conflict warnings for double-booked teachers.

11.7 Notices & Communication

FR-20: The Admin shall be able to target a notice to Everyone, a specific class, or Staff only, and choose delivery channels (Website, Student Portal, WhatsApp).

FR-21: The system shall log the delivery status of every WhatsApp message sent.

11.8 Website Content Management

FR-22: The Admin shall be able to add/edit/remove Gallery albums, Achievements, News, and Faculty entries without developer involvement.

FR-23: An Admissions Enquiry form submission shall create a new entry in the Admin’s Enquiry Management list automatically.

12. Non-Functional Requirements

12.1 Performance

Public website pages shall load within 3 seconds on an average 4G connection.

The system shall remain usable on a basic Android smartphone, not only desktops.

12.2 Security

All traffic shall be served over HTTPS.

Passwords shall be stored encrypted (hashed), never in plain text.

Role-based access control shall be enforced at the backend (API) level, not only hidden in the interface.

Regular automated backups of the database shall be maintained.

12.3 Availability & Reliability

Target uptime of 99%+ for the public website and portals.

Planned maintenance shall be scheduled outside school working hours where possible.

12.4 Usability

Interfaces shall be simple enough for a non-technical teacher to use after a single short training session.

Key actions (mark attendance, post a notice) shall be reachable within 2–3 taps from the dashboard.

12.5 Compliance

The website shall display the CBSE Mandatory Public Disclosure information prominently on the Home Page, per CBSE Affiliation Bye-Laws Clause 2.4.9.

Student and parent personal data (being data relating to minors) shall be stored securely and never shared with third parties beyond what is required to operate the platform (e.g. payment gateway, WhatsApp provider).

12.6 Scalability

The system architecture shall support adding more classes, sections, or even additional school branches in the future without a redesign.

13. High-Level Data Entities

This is not a full database schema — it lists the core records the system will store, as a reference for both the school and the developer.

Entity

Holds

School

Name, logo, address, affiliation number, settings

AcademicYear

Session start/end, current active year

Class / Section

Class name, section, class teacher

Subject

Subject name, assigned classes

Student

Personal details, class/section, parent contact, documents

Parent / Guardian

Name, phone (WhatsApp), email, linked student(s)

Staff

Personal details, role, assigned subjects/classes

Attendance

Date, student, status, marked by

FeeStructure / FeeTransaction

Fee heads, amounts, due dates, payment records, receipts

Exam / Mark / ReportCard

Exam definitions, marks per student per subject, generated report cards

Homework

Class, subject, description, due date, attachments, submissions

Notice

Title, content, audience, channels, schedule

AdmissionEnquiry

Submitted form data, status, follow-up notes

TimetableSlot

Class, day, period, subject, teacher

User

Login credentials, role, linked Student/Staff/Parent record

WhatsAppMessageLog

Recipient, message type, content, delivery status, timestamp

14. Third-Party Integrations

Integration

Purpose

Razorpay

Online fee collection, payment status, receipts

WhatsApp Business Cloud API

Attendance alerts, fee reminders, results, notices, two-way replies

Cloudinary

Storage and optimised delivery of photos, gallery images, documents

Clerk

Secure, role-based authentication for Admin / Teacher / Student

Google Maps

Embedded location on the Contact Us page

15. Future Scope — AI & Automation Add-Ons

These are not part of the core build costed in the Proposal document. Each is scoped and priced separately and can be switched on as the school is ready.

15.1  AI Call Assistant

Purpose: Answers routine parent phone calls automatically, 24/7, so office staff handle only what truly needs a human.

Answers common queries: results, fee dues, school timings, holidays, syllabus

Escalates to a human for anything it cannot confidently answer

Full call log visible to Admin (Section 6.14)

15.2  AI WhatsApp Chat Assistant

Purpose: A chat version of the same idea, for parents who prefer texting over calling.

Parents ask in plain language: “What’s my child’s attendance?”, “Is the fee due?” — answered instantly from the school’s own data

15.3  Automated Admission Follow-Up

Purpose: Increases admission conversion without extra staff effort.

Automatic WhatsApp + reminder sequence for enquiries that haven’t responded or visited

15.4  Automated Fee Reminders

Purpose: Recovers dues without manual chasing.

Scheduled WhatsApp reminders before, on, and after the due date, with escalation

15.5  Auto Report-Card Remarks

Purpose: Saves teachers hours during exam season.

Generates a draft teacher remark from each student’s marks, for the teacher to review and approve

15.6  Social Media Auto-Posting

Purpose: Keeps the school’s public image active with no ongoing staff effort.

Scheduled posts of achievements, events, and quotes to the school’s social media

16. Glossary

Term

Meaning

SRS

Software Requirements Specification — this document

CRUD

Create, Read, Update, Delete — the basic data actions a role may be allowed to perform

RBAC

Role-Based Access Control — restricting access by user role

CMS

Content Management System — lets non-technical staff edit website content

API

Application Programming Interface — how the frontend and backend communicate

OTP

One-Time Password — used for secure login

TC

Transfer Certificate

CBSE Mandatory Disclosure

A CBSE-required public webpage showing school compliance information

End of Document. Please review every section with the school and note any changes before development begins. Pricing and timeline are covered separately in the Proposal document.