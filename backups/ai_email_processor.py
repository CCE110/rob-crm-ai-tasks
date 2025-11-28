#!/usr/bin/env python3
"""
AI Email Task Processor
Analyzes forwarded emails and suggests tasks
"""

import imaplib
import email
from email.header import decode_header
import json
from datetime import datetime, timedelta
from task_manager import TaskManager
from anthropic import Anthropic
from dotenv import load_dotenv
import os

load_dotenv()

class AIEmailProcessor:
    def __init__(self):
        self.tm = TaskManager()
        self.claude = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
        
        # Gmail settings for robcrm.ai@gmail.com
        self.gmail_user = "robcrm.ai@gmail.com"
        self.gmail_password = "sgho tbwr optz yxie"
        
        # Business IDs
        self.businesses = {
            'Cloud Clean Energy': 'feb14276-5c3d-4fcf-af06-9a8f54cf7159',
            'AI Project Pro': 'ec5d7aab-8d74-4ef2-9d92-01b143c68c82'
        }
    
    def process_forwarded_emails(self):
        """Check for new forwarded emails and analyze them"""
        print("🤖 AI Email Processor Starting...")
        print("📧 Checking robcrm.ai@gmail.com for forwarded emails...")
        
        try:
            # Connect to Gmail
            mail = imaplib.IMAP4_SSL('imap.gmail.com')
            mail.login(self.gmail_user, self.gmail_password)
            mail.select('inbox')
            
            # Search for unread emails
            status, messages = mail.search(None, 'UNSEEN')
            
            if not messages[0]:
                print("📭 No new emails to process")
                return
            
            email_count = len(messages[0].split())
            print(f"📬 Found {email_count} new emails to analyze")
            
            suggestions = []
            
            for msg_id in messages[0].split():
                suggestion = self.analyze_email(mail, msg_id)
                if suggestion:
                    suggestions.append(suggestion)
            
            mail.close()
            mail.logout()
            
            # Show suggestions to user
            if suggestions:
                self.present_suggestions(suggestions)
            else:
                print("🤷‍♂️ No actionable tasks found in emails")
                
        except Exception as e:
            print(f"❌ Error processing emails: {e}")
    
    def analyze_email(self, mail, msg_id):
        """Use Claude AI to analyze email and suggest tasks"""
        try:
            # Get email content
            status, msg_data = mail.fetch(msg_id, '(RFC822)')
            email_body = email.message_from_bytes(msg_data[0][1])
            
            # Extract email details
            subject = decode_header(email_body['Subject'])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode()
            
            sender = email_body['From']
            
            # Get email content
            content = self.extract_email_content(email_body)
            
            print(f"📧 Analyzing: {subject}")
            print(f"From: {sender}")
            
            # Ask Claude to analyze
            prompt = f"""
Analyze this forwarded email and determine if any tasks should be created for Rob's business management.

EMAIL DETAILS:
From: {sender}
Subject: {subject}
Content: {content}

BUSINESSES:
- Cloud Clean Energy (solar energy, main business operations)
- AI Project Pro (AI consulting business)

Please determine:
1. Should any tasks be created from this email?
2. What specific tasks are needed?
3. Which business does this relate to?
4. What priority level?
5. When should it be due?

Respond in JSON format:
{{
    "create_tasks": true/false,
    "reason": "Brief explanation",
    "tasks": [
        {{
            "title": "Clear, actionable task title",
            "description": "What needs to be done and why",
            "business": "Cloud Clean Energy" or "AI Project Pro",
            "priority": "low/medium/high/urgent",
            "due_date": "YYYY-MM-DD or null if not time-sensitive",
            "due_time": "HH:MM or null",
            "is_meeting": true/false,
            "context": "Key details from the email"
        }}
    ]
}}
"""

            response = self.claude.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse Claude's response
            try:
                analysis = json.loads(response.content[0].text)
                if analysis.get('create_tasks'):
                    return {
                        'email_subject': subject,
                        'email_sender': sender,
                        'analysis': analysis
                    }
            except json.JSONDecodeError:
                print(f"⚠️ Could not parse AI response for email: {subject}")
                print(f"Raw response: {response.content[0].text}")
            
        except Exception as e:
            print(f"❌ Error analyzing email: {e}")
        
        return None
    
    def extract_email_content(self, email_body):
        """Extract text content from email"""
        content = ""
        
        if email_body.is_multipart():
            for part in email_body.walk():
                if part.get_content_type() == "text/plain":
                    content += part.get_payload(decode=True).decode('utf-8', errors='ignore')
        else:
            content = email_body.get_payload(decode=True).decode('utf-8', errors='ignore')
        
        return content[:2000]  # Limit content length
    
    def present_suggestions(self, suggestions):
        """Show task suggestions to user for approval"""
        print("\n" + "="*60)
        print("🤖 AI TASK SUGGESTIONS")
        print("="*60)
        
        for i, suggestion in enumerate(suggestions, 1):
            analysis = suggestion['analysis']
            
            print(f"\n📧 EMAIL {i}: {suggestion['email_subject']}")
            print(f"From: {suggestion['email_sender']}")
            print(f"AI Analysis: {analysis['reason']}")
            
            for j, task in enumerate(analysis['tasks'], 1):
                print(f"\n   🔍 SUGGESTED TASK {j}:")
                print(f"   Title: {task['title']}")
                print(f"   Business: {task['business']}")
                print(f"   Priority: {task['priority']}")
                print(f"   Due: {task.get('due_date', 'No specific date')}{' at ' + task.get('due_time', '') if task.get('due_time') else ''}")
                print(f"   Description: {task['description']}")
                
                # Ask for approval
                approve = input(f"\n   ✅ Create this task? (y/N): ").lower().startswith('y')
                
                if approve:
                    self.create_task_from_suggestion(task)
                else:
                    print("   ⏭️ Skipped")
    
    def create_task_from_suggestion(self, task_data):
        """Create approved task in database"""
        try:
            business_id = self.businesses.get(task_data['business'])
            if not business_id:
                print(f"   ❌ Unknown business: {task_data['business']}")
                return
            
            # Create task
            result = self.tm.supabase.table('tasks').insert({
                'business_id': business_id,
                'title': task_data['title'],
                'description': task_data['description'],
                'due_date': task_data.get('due_date'),
                'due_time': task_data.get('due_time'),
                'priority': task_data['priority'],
                'is_meeting': task_data.get('is_meeting', False)
            }).execute()
            
            if result.data:
                task = result.data[0]
                print(f"   ✅ Task created: {task['title']}")
                
                # Send confirmation email
                self.tm.send_task_confirmation_email(task['id'])
                print(f"   📧 Confirmation email sent!")
            else:
                print(f"   ❌ Failed to create task")
                
        except Exception as e:
            print(f"   ❌ Error creating task: {e}")

if __name__ == "__main__":
    processor = AIEmailProcessor()
    processor.process_forwarded_emails()
