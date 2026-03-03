from flask import Flask, render_template, request, jsonify
import asyncio
from playwright.async_api import async_playwright
import nest_asyncio
import indian_names

app = Flask(__name__)

# Apply nest_asyncio to fix event loop issues
nest_asyncio.apply()

# Store active tasks
active_tasks = set()

# Initialize indian_names to generate random Indian names
def generate_random_name():
    return indian_names.get_full_name()

async def join_meeting_after_navigation(page):
    try:
        # Wait for the name input field
        await page.wait_for_selector('input[type="text"]', timeout=60000)

        # Generate a random Indian name
        random_name = generate_random_name()

        # Enter the name
        await page.fill('input[type="text"]', random_name)

        # Check for password field
        password_field = await page.query_selector('input[type="password"]')
        if password_field:
            await page.fill('input[type="password"]', "your_passcode_here")  # Replace with actual passcode
            await page.wait_for_selector('button.preview-join-button', timeout=60000)
            await page.click('button.preview-join-button')
        else:
            await page.wait_for_selector('button.preview-join-button', timeout=60000)
            await page.click('button.preview-join-button')

        # Print once after joining the meeting
        print(f"{random_name} has joined the meeting. The meeting will last for 7200 seconds.")

        # Keep the meeting open for 7200 seconds (2 hours)
        await asyncio.sleep(7200)  # 7200 seconds = 2 hours
        print(f"{random_name} stayed in the meeting for 7200 seconds.")

    except asyncio.CancelledError:
        print(f"{random_name} was removed from the meeting.")
    except Exception:
        pass  # Suppress errors to avoid unnecessary logs

async def open_browser_and_join(meeting_name, meeting_code, meeting_passcode):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # Create an incognito context
        context = await browser.new_context()

        # Open new page
        page = await context.new_page()

        # Go to the website
        await page.goto("http://roaring-squirrel-4da56c.netlify.app/")

        # Fill in the meeting details
        await page.wait_for_selector('input[type="text"]', timeout=60000)
        await page.locator('input[type="text"]').nth(0).fill(meeting_name)
        await page.locator('input[type="text"]').nth(1).fill(meeting_code)
        await page.locator('input[type="text"]').nth(2).fill(meeting_passcode)

        # Click Save Meeting
        await page.click("button:has-text('Save Meeting')")

        # Wait before clicking Join Meeting
        await asyncio.sleep(3)

        # Click Join Meeting and wait for the new page
        async with context.expect_page() as new_page_event:
            await page.click("button:has-text('Join Meeting')")

        # Get the new page
        new_page = await new_page_event.value

        # Perform the join process
        await join_meeting_after_navigation(new_page)

        # Close the browser after the total time
        await browser.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start', methods=['POST'])
def start():
    data = request.json
    meeting_name = data.get('meeting_name')
    meeting_code = data.get('meeting_code')
    meeting_passcode = data.get('meeting_passcode')
    num_users = int(data.get('num_users'))

    # Generate random names for members
    members = [generate_random_name() for _ in range(num_users)]

    # Run the tasks concurrently
    tasks = [asyncio.create_task(open_browser_and_join(meeting_name, meeting_code, meeting_passcode)) for _ in range(num_users)]
    for task in tasks:
        active_tasks.add(task)
        task.add_done_callback(active_tasks.discard)  # Remove task from active_tasks when done

    return jsonify({
        "status": "success",
        "message": f"{num_users} users joined the meeting.",
        "members": members  # Return the list of members
    })

@app.route('/end', methods=['POST'])
def end():
    # Cancel all active tasks
    for task in active_tasks:
        task.cancel()
    active_tasks.clear()

    return jsonify({
        "status": "success",
        "message": "All meeting tasks have been stopped."
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
