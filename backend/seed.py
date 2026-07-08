import asyncio
from datetime import date
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.database import Base
from app.models.school import School
from app.models.academic import AcademicYear, Class, Section, Subject
from app.models.student import Student, Parent
from app.models.staff import Staff, StaffSubjectAssignment
from app.models.user import User, UserRole
from app.models.cms import GalleryAlbum, GalleryImage, Achievement, NewsEvent
from app.models.notice import Notice, NoticeAudience


async def seed():
    print("Connecting to database...")
    engine = create_async_engine("sqlite+aiosqlite:///./school.db")
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    print("Dropping all existing tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        print("Creating all tables...")
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        print("Seeding school profile...")
        school = School(
            name="Knowledge Development Kindergarten Academy",
            logo_url="https://images.unsplash.com/photo-1580582932707-520aed937b7b?w=200&h=200&fit=crop",
            address="Sector 5, Knowledge Campus, Near City Park, New Delhi, 110001",
            affiliation_number="1234567",
            contact_email="info@knowledgeacademy.edu.in",
            contact_phone="+91 98765 43210",
            settings={"theme": "indigo", "allow_online_fees": True}
        )
        session.add(school)

        print("Seeding academic year...")
        year = AcademicYear(
            label="2026-27",
            start_date=date(2026, 4, 1),
            end_date=date(2027, 3, 31),
            is_current=True
        )
        session.add(year)
        await session.flush()

        print("Seeding classes...")
        class_lkg = Class(name="LKG", numeric_order=1)
        class_ukg = Class(name="UKG", numeric_order=2)
        class_1 = Class(name="Class 1", numeric_order=3)
        class_2 = Class(name="Class 2", numeric_order=4)
        session.add_all([class_lkg, class_ukg, class_1, class_2])
        await session.flush()

        print("Seeding sections...")
        sec_lkg_a = Section(name="A", class_id=class_lkg.id)
        sec_ukg_a = Section(name="A", class_id=class_ukg.id)
        sec_1_a = Section(name="A", class_id=class_1.id)
        sec_1_b = Section(name="B", class_id=class_1.id)
        session.add_all([sec_lkg_a, sec_ukg_a, sec_1_a, sec_1_b])
        await session.flush()

        print("Seeding subjects...")
        sub_eng = Subject(name="English", code="ENG101")
        sub_math = Subject(name="Mathematics", code="MAT101")
        sub_evs = Subject(name="Environmental Studies", code="EVS101")
        sub_sci = Subject(name="Science", code="SCI101")
        session.add_all([sub_eng, sub_math, sub_evs, sub_sci])
        await session.flush()

        print("Seeding staff...")
        staff_principal = Staff(
            first_name="Anita",
            last_name="Sharma",
            phone="9876543210",
            email="principal@knowledgeacademy.edu.in",
            qualification="M.A., B.Ed.",
            designation="Principal"
        )
        staff_teacher1 = Staff(
            first_name="Sunita",
            last_name="Kaul",
            phone="9876543211",
            email="sunita@knowledgeacademy.edu.in",
            qualification="M.Sc. (Maths), B.Ed.",
            designation="PRT Mathematics"
        )
        staff_teacher2 = Staff(
            first_name="Ramesh",
            last_name="Joshi",
            phone="9876543212",
            email="ramesh@knowledgeacademy.edu.in",
            qualification="M.Sc. (Physics), B.Ed.",
            designation="TGT Science"
        )
        session.add_all([staff_principal, staff_teacher1, staff_teacher2])
        await session.flush()

        # Update section class teachers
        sec_1_a.class_teacher_id = staff_teacher1.id
        await session.flush()

        print("Seeding staff subject assignments...")
        assign1 = StaffSubjectAssignment(
            staff_id=staff_teacher1.id,
            subject_id=sub_math.id,
            class_id=class_1.id,
            section_id=sec_1_a.id
        )
        assign2 = StaffSubjectAssignment(
            staff_id=staff_teacher2.id,
            subject_id=sub_sci.id,
            class_id=class_1.id,
            section_id=sec_1_a.id
        )
        session.add_all([assign1, assign2])

        print("Seeding students and parents...")
        student1 = Student(
            admission_number="ADM-00001",
            first_name="Aarav",
            last_name="Sharma",
            dob=date(2020, 5, 12),
            gender="male",
            photo_url="https://images.unsplash.com/photo-1544717305-2782549b5136?w=200&fit=crop",
            class_id=class_1.id,
            section_id=sec_1_a.id,
            roll_number=1,
            address="Flat 102, Green Avenue, New Delhi",
            documents={}
        )
        student2 = Student(
            admission_number="ADM-00002",
            first_name="Riya",
            last_name="Verma",
            dob=date(2020, 8, 25),
            gender="female",
            photo_url="https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=200&fit=crop",
            class_id=class_1.id,
            section_id=sec_1_a.id,
            roll_number=2,
            address="House 44, Park Street, New Delhi",
            documents={}
        )
        session.add_all([student1, student2])
        await session.flush()

        parent1 = Parent(
            name="Rakesh Sharma",
            phone="9876543220",
            email="rakesh@example.com",
            relation="father",
            student_id=student1.id
        )
        parent2 = Parent(
            name="Suman Verma",
            phone="9876543221",
            email="suman@example.com",
            relation="mother",
            student_id=student2.id
        )
        session.add_all([parent1, parent2])

        print("Seeding login users (see DEMO_CREDENTIALS.md)...")
        from app.services.security import hash_password

        user_admin = User(
            login_id="admin",
            password_hash=hash_password("Admin@2026"),
            email="admin@knowledgeacademy.edu.in",
            phone="9876543210",
            role=UserRole.SUPER_ADMIN,
            is_active=True
        )
        user_teacher = User(
            login_id="EMP-001",
            password_hash=hash_password("Teach@2026"),
            email="sunita@knowledgeacademy.edu.in",
            phone="9876543211",
            role=UserRole.TEACHER,
            linked_staff_id=staff_teacher1.id,
            is_active=True
        )
        user_student = User(
            login_id="ADM-00001",
            password_hash=hash_password("Study@2026"),
            email="aarav@example.com",
            phone="9876543220",
            role=UserRole.STUDENT,
            linked_student_id=student1.id,
            is_active=True
        )
        session.add_all([user_admin, user_teacher, user_student])

        print("Seeding CMS gallery, achievements, and events...")
        album1 = GalleryAlbum(title="Annual Day 2025", description="Drama, music, and annual prize distribution.")
        album2 = GalleryAlbum(title="Sports Meet 2025", description="Obstacle races, tracks, and group awards.")
        session.add_all([album1, album2])
        await session.flush()

        img1 = GalleryImage(album_id=album1.id, image_url="https://images.unsplash.com/photo-1511578314322-379afb476865?w=600&fit=crop", caption="Drama performance")
        img2 = GalleryImage(album_id=album2.id, image_url="https://images.unsplash.com/photo-1502086223501-7ea6ecd79368?w=600&fit=crop", caption="Running finish line")
        session.add_all([img1, img2])

        ach1 = Achievement(title="State Science Talent Search Winner", description="Awarded for water purifier model.", date=date(2025, 11, 20), category="academics")
        ach2 = Achievement(title="District Chess Gold Medalist", description="Under-14 gold sweep.", date=date(2025, 12, 10), category="sports")
        session.add_all([ach1, ach2])

        event1 = NewsEvent(title="Reopening of School after Summer Vacation", description="Classes resume on July 1st, 2026.", event_date=date(2026, 7, 1), is_published=True)
        session.add_all([event1])

        print("Seeding sample notice...")
        notice = Notice(
            title="School Reopening circular",
            content="Classes for Nursery to Class X will resume on July 1st, 2026. Please collect syllabus folders.",
            audience=NoticeAudience.EVERYONE,
            channels=["website", "portal"],
            published_at=date(2026, 6, 20)
        )
        session.add(notice)

        await session.commit()
        print("Database seeding completed successfully! sqlite db is ready.")


if __name__ == "__main__":
    asyncio.run(seed())
