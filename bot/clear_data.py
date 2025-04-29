import json
import os

def clear_databases():
    # Initial empty structures
    empty_states = {}
    empty_messages = {}
    
    # Write empty user states
    with open('user_states.json', 'w') as f:
        json.dump(empty_states, f, indent=2)
    
    # Write empty message history
    with open('message_history.json', 'w') as f:
        json.dump(empty_messages, f, indent=2)
        
    print("Databases cleared successfully!")

if __name__ == "__main__":
    clear_databases()