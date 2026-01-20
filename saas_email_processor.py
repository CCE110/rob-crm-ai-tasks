"""
Jottask SaaS Email Processor
Multi-tenant email processing for all users
"""

import os
import imaplib
import email
from email.header import decode_header
from datetime import datetime, timedelta
import pytz
import time
import json
from supabase import create_client, Client
from anthropic import Anthropic

# Initialize clients
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

anthropic = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))


def get_active_email_connections():
    """Get all active email connections from all users"""
    result = supabase.table('email_connections')\
        .select('*, users(id, email, timezone, subscription_tier)')\
        .eq('is_active', True)\
        .execute()
    return result.data or []


def connect_to_imap(email_address, password, provider='gmail'):
    """Connect to IMAP server"""
    if provider == 'gmail':
        server = 'imap.gmail.com'
    else:
        server = 'imap.gmail.com'  # Default to Gmail

    try:
        imap = imaplib.IMAP4_SSL(server)
        imap.login(email_address, password)
        return imap
    except Exception as e:
        print(f"❌ Failed to connect to {email_address}: {e}")
        return None


def decode_email_subject(subject):
    """Decode email subject handling various encodings"""
    if not subject:
        return "No Subject"

    decoded_parts = decode_header(subject)
    decoded_subject = ""

    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            try:
                decoded_subject += part.decode(encoding or 'utf-8', errors='replace')
            except:
                decoded_subject += part.decode('utf-8', errors='replace')
        else:
            decoded_subject += part

    return decoded_subject.strip()


def get_email_body(msg):
    """Extract email body text"""
    body = ""

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body = payload.decode('utf-8', errors='replace')
                        break
                except:
                    pass
    else:
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode('utf-8', errors='replace')
        except:
            pass

    return body[:5000]  # Limit body size


def analyze_email_with_ai(subject, body, from_email, user_timezone):
    """Use Claude to analyze email and extract task information"""
    tz = pytz.timezone(user_timezone)
    now = datetime.now(tz)

    prompt = f"""Analyze this email and determine if it contains an actionable task.

From: {from_email}
Subject: {subject}
Body:
{body[:3000]}

Current date/time: {now.strftime('%Y-%m-%d %H:%M')} ({user_timezone})

If this email contains a task or follow-up needed, respond with JSON:
{{
    "is_task": true,
    "title": "brief task title",
    "description": "task details",
    "due_date": "YYYY-MM-DD",
    "due_time": "HH:MM",
    "priority": "low|medium|high|urgent",
    "client_name": "name if mentioned",
    "client_email": "{from_email}",
    "project_name": "project if mentioned"
}}

If this is NOT an actionable task (newsletter, spam, notification, etc), respond with:
{{
    "is_task": false,
    "reason": "brief reason"
}}

Respond with only valid JSON, no other text."""

    try:
        response = anthropic.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text.strip()

        # Clean up response if needed
        if response_text.startswith('```'):
            response_text = response_text.split('```')[1]
            if response_text.startswith('json'):
                response_text = response_text[4:]

        return json.loads(response_text)

    except Exception as e:
        print(f"❌ AI analysis failed: {e}")
        return {"is_task": False, "reason": "AI analysis failed"}


def check_if_email_processed(email_id, user_id):
    """Check if email has already been processed for this user"""
    result = supabase.table('processed_emails')\
        .select('id')\
        .eq('email_id', f"{user_id}_{email_id}")\
        .execute()
    return len(result.data) > 0


def mark_email_processed(email_id, user_id):
    """Mark email as processed"""
    try:
        supabase.table('processed_emails').insert({
            'email_id': f"{user_id}_{email_id}"
        }).execute()
    except:
        pass  # Ignore if already exists


def create_task_for_user(user_id, task_data):
    """Create a task for a specific user"""
    try:
        task = {
            'user_id': user_id,
            'title': task_data.get('title', 'Email Task'),
            'description': task_data.get('description'),
            'due_date': task_data.get('due_date'),
            'due_time': task_data.get('due_time', '09:00') + ':00',
            'priority': task_data.get('priority', 'medium'),
            'status': 'pending',
            'client_name': task_data.get('client_name'),
            'client_email': task_data.get('client_email'),
            'project_name': task_data.get('project_name')
        }

        result = supabase.table('tasks').insert(task).execute()

        if result.data:
            print(f"✅ Task created: {task['title']}")
            return result.data[0]

    except Exception as e:
        print(f"❌ Failed to create task: {e}")

    return None


def process_emails_for_connection(connection):
    """Process emails for a single connection"""
    user_id = connection['user_id']
    email_address = connection['email_address']
    password = connection.get('imap_password')
    provider = connection.get('provider', 'gmail')
    user_data = connection.get('users', {})
    user_timezone = user_data.get('timezone', 'Australia/Brisbane')

    print(f"\n📧 Processing emails for: {email_address}")

    if not password:
        print(f"⚠️ No password configured for {email_address}")
        return

    # Connect to IMAP
    imap = connect_to_imap(email_address, password, provider)
    if not imap:
        return

    try:
        # Select inbox
        imap.select('INBOX')

        # Search for recent unread emails (last 24 hours)
        date_since = (datetime.now() - timedelta(days=1)).strftime('%d-%b-%Y')
        _, messages = imap.search(None, f'(SINCE {date_since} UNSEEN)')

        email_ids = messages[0].split()
        print(f"📬 Found {len(email_ids)} unread emails")

        # Process newest first, limit to 10
        for email_id in reversed(email_ids[:10]):
            email_id_str = email_id.decode()

            # Check if already processed
            if check_if_email_processed(email_id_str, user_id):
                continue

            # Fetch email
            _, msg_data = imap.fetch(email_id, '(RFC822)')
            email_body = msg_data[0][1]
            msg = email.message_from_bytes(email_body)

            # Extract details
            subject = decode_email_subject(msg.get('Subject', ''))
            from_header = msg.get('From', '')
            from_email = from_header.split('<')[-1].replace('>', '').strip() if '<' in from_header else from_header

            print(f"  📩 Processing: {subject[:50]}...")

            # Skip emails from the same address (own sent items)
            if from_email.lower() == email_address.lower():
                mark_email_processed(email_id_str, user_id)
                continue

            # Get body and analyze
            body = get_email_body(msg)
            analysis = analyze_email_with_ai(subject, body, from_email, user_timezone)

            if analysis.get('is_task'):
                # Create task
                task = create_task_for_user(user_id, analysis)

                if task:
                    # Add email as note to task
                    try:
                        supabase.table('task_notes').insert({
                            'task_id': task['id'],
                            'content': f"Created from email:\n\n{body[:1000]}",
                            'source': 'email',
                            'source_email_subject': subject,
                            'source_email_from': from_email,
                            'created_by': 'system'
                        }).execute()
                    except:
                        pass

            # Mark as processed
            mark_email_processed(email_id_str, user_id)

        # Update last sync time
        supabase.table('email_connections').update({
            'last_sync_at': datetime.utcnow().isoformat()
        }).eq('id', connection['id']).execute()

    except Exception as e:
        print(f"❌ Error processing emails: {e}")

    finally:
        try:
            imap.logout()
        except:
            pass


def run_email_processor():
    """Main processor loop - runs continuously"""
    print("🚀 Starting Jottask SaaS Email Processor")
    print("=" * 50)

    while True:
        try:
            # Get all active connections
            connections = get_active_email_connections()
            print(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📊 Active email connections: {len(connections)}")

            # Process each connection
            for connection in connections:
                try:
                    process_emails_for_connection(connection)
                except Exception as e:
                    print(f"❌ Error with connection {connection.get('email_address')}: {e}")

            print(f"\n😴 Sleeping for 15 minutes...")
            time.sleep(900)  # 15 minutes

        except KeyboardInterrupt:
            print("\n👋 Shutting down email processor...")
            break
        except Exception as e:
            print(f"❌ Processor error: {e}")
            time.sleep(60)  # Wait 1 minute on error


if __name__ == '__main__':
    from dotenv import load_dotenv
    load_dotenv()
    run_email_processor()
