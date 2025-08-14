#!/usr/bin/env python
"""
Script to populate sample performance evaluation data
"""
import os
import sys
import django
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'university_staff.settings')
django.setup()

from staff.models import Staff, PerformanceReview, PerformanceGoal, StaffFeedback, SelfAssessment

def populate_performance_data():
    print("Populating performance evaluation data...")
    
    # Get some staff members
    staff_members = Staff.objects.filter(status='active')[:10]
    
    if not staff_members:
        print("No active staff found. Please add staff first.")
        return
    
    # Create performance reviews
    reviews_created = 0
    goals_created = 0
    feedback_created = 0
    assessments_created = 0
    
    for i, staff in enumerate(staff_members):
        supervisor = staff.get_supervisor()
        if not supervisor:
            # Use the first staff member as supervisor if none assigned
            supervisor = staff_members[0] if staff_members[0] != staff else staff_members[1] if len(staff_members) > 1 else staff
        
        # Create 2-3 reviews per staff member
        for review_num in range(2):
            review_start = date.today() - relativedelta(months=6 + (review_num * 6))
            review_end = review_start + relativedelta(months=6)
            scheduled_date = datetime.combine(review_end + timedelta(days=7), datetime.min.time())
            
            # Determine status and completion
            if review_num == 0:  # Most recent review
                status = 'completed' if i % 3 == 0 else 'scheduled'
                completed_date = scheduled_date + timedelta(days=2) if status == 'completed' else None
                overall_rating = [3, 4, 5, 4, 3, 5, 4, 3, 4, 5][i] if status == 'completed' else None
            else:  # Older review
                status = 'completed'
                completed_date = scheduled_date + timedelta(days=2)
                overall_rating = [4, 3, 5, 4, 3, 4, 5, 3, 4, 4][i]
            \n            review = PerformanceReview.objects.create(\n                staff=staff,\n                supervisor=supervisor,\n                review_period_start=review_start,\n                review_period_end=review_end,\n                scheduled_date=scheduled_date,\n                completed_date=completed_date,\n                status=status,\n                overall_rating=overall_rating,\n                strengths=f\"Strong performance in {staff.position} role. Excellent communication skills and team collaboration.\" if status == 'completed' else \"\",\n                areas_for_improvement=f\"Could improve time management and project planning skills.\" if status == 'completed' else \"\",\n                supervisor_comments=f\"{staff.first_name} has shown consistent growth and dedication to their role.\" if status == 'completed' else \"\",\n                staff_comments=f\"I appreciate the feedback and look forward to continuing my development.\" if status == 'completed' else \"\"\n            )\n            reviews_created += 1\n            \n            # Create 2-3 goals per review\n            goal_titles = [\n                \"Improve project delivery time\",\n                \"Enhance technical skills\",\n                \"Develop leadership capabilities\",\n                \"Increase customer satisfaction\",\n                \"Complete professional certification\"\n            ]\n            \n            for goal_num in range(2 + (i % 2)):\n                goal_title = goal_titles[goal_num % len(goal_titles)]\n                target_date = review_end + relativedelta(months=3)\n                \n                # Set progress based on review status\n                if status == 'completed':\n                    progress = [80, 60, 90, 75, 100][goal_num % 5]\n                    goal_status = 'completed' if progress == 100 else 'in_progress'\n                else:\n                    progress = [20, 40, 10, 30, 50][goal_num % 5]\n                    goal_status = 'in_progress' if progress > 0 else 'not_started'\n                \n                PerformanceGoal.objects.create(\n                    review=review,\n                    title=goal_title,\n                    description=f\"Detailed description for {goal_title.lower()} with specific measurable outcomes.\",\n                    target_date=target_date,\n                    status=goal_status,\n                    progress_percentage=progress,\n                    notes=f\"Progress update: Currently at {progress}% completion with good momentum.\"\n                )\n                goals_created += 1\n            \n            # Create feedback for completed reviews\n            if status == 'completed':\n                # Self assessment\n                SelfAssessment.objects.create(\n                    staff=staff,\n                    review=review,\n                    achievements=f\"Successfully completed major projects in {staff.department.name}. Improved efficiency by 15%.\",\n                    challenges_faced=\"Faced some challenges with new technology adoption but overcame them through training.\",\n                    skills_developed=\"Developed stronger analytical and problem-solving skills through various projects.\",\n                    training_needs=\"Would benefit from advanced training in project management and leadership.\",\n                    career_goals=\"Aspire to take on more leadership responsibilities and contribute to strategic planning.\",\n                    self_rating=[3, 4, 4, 3, 4, 5, 3, 4, 4, 3][i]\n                )\n                assessments_created += 1\n                \n                # Peer feedback (from other staff members)\n                if len(staff_members) > 1:\n                    peer = staff_members[(i + 1) % len(staff_members)]\n                    if peer != staff:\n                        StaffFeedback.objects.create(\n                            staff=peer,\n                            about_staff=staff,\n                            review=review,\n                            feedback_type='peer',\n                            rating=[4, 3, 5, 4, 3, 4, 5, 3, 4, 4][i],\n                            comments=f\"{staff.first_name} is a reliable team member who consistently delivers quality work.\",\n                            anonymous=i % 3 == 0  # Some anonymous feedback\n                        )\n                        feedback_created += 1\n                \n                # Supervisor feedback\n                if supervisor != staff:\n                    StaffFeedback.objects.create(\n                        staff=supervisor,\n                        about_staff=staff,\n                        review=review,\n                        feedback_type='peer',\n                        rating=overall_rating,\n                        comments=f\"As {staff.first_name}'s supervisor, I'm pleased with their performance and growth.\",\n                        anonymous=False\n                    )\n                    feedback_created += 1\n    \n    print(f\"Successfully created:\")\n    print(f\"  - {reviews_created} performance reviews\")\n    print(f\"  - {goals_created} performance goals\")\n    print(f\"  - {feedback_created} feedback entries\")\n    print(f\"  - {assessments_created} self assessments\")\n    print(\"\\nPerformance evaluation data populated successfully!\")\n\nif __name__ == '__main__':\n    populate_performance_data()