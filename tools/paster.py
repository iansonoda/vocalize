import pyperclip
import pyautogui
import time
import sys

def paste_text(text):
    """
    Copies the text to the clipboard and simulates Cmd+V to paste it into the active window.
    """
    if not text:
        print("⚠️ No text to paste.")
        return

    print(f"📋 Copying to clipboard: '{text}'")
    # Save the original clipboard content so we don't destroy what the user had there
    original_clipboard = pyperclip.paste()
    
    try:
        # Copy our new text
        pyperclip.copy(text)
        
        # Give the system slightly enough time to register the clipboard change
        time.sleep(0.1)
        
        # Simulate Cmd+V (macOS paste)
        print("⌨️ Simulating Cmd+V...")
        pyautogui.hotkey('command', 'v')
        
    except Exception as e:
        print(f"❌ Failed to paste text: {e}")
    finally:
        # Note: Depending on how fast the target app processes the paste event, 
        # restoring the clipboard too quickly might paste the old text.
        # We might need to adjust this delay later if we want to restore the old clipboard.
        # For a "Wispr Flow clone", usually it's fine to leave the transcribed text in the clipboard.
        pass

if __name__ == "__main__":
    if len(sys.argv) > 1:
        paste_text(sys.argv[1])
    else:
        print("Usage: python paster.py 'Text to paste'")
