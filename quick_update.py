import sqlite3
import os
from datetime import datetime

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_statistics():
    conn = sqlite3.connect('mpcb_grievance.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM complaints')
    total = cursor.fetchone()[0]
    
    cursor.execute('SELECT status, COUNT(*) FROM complaints GROUP BY status')
    status_counts = cursor.fetchall()
    
    conn.close()
    
    print(f"\n📊 STATISTICS:")
    print(f"   Total Complaints: {total}")
    for status, count in status_counts:
        print(f"   {status}: {count}")

def view_complaint_details(complaint_id):
    conn = sqlite3.connect('mpcb_grievance.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM complaints WHERE id = ?', (complaint_id,))
    complaint = cursor.fetchone()
    conn.close()
    
    if complaint:
        print("\n" + "="*60)
        print(f"COMPLAINT DETAILS: {complaint_id}")
        print("="*60)
        print(f"Name: {complaint[1]}")
        print(f"Email: {complaint[2]}")
        print(f"Phone: {complaint[3]}")
        print(f"Type: {complaint[4]}")
        print(f"Location: {complaint[5]}")
        print(f"Description: {complaint[7]}")
        print(f"Current Status: {complaint[9]}")
        print(f"Filed On: {complaint[10]}")
        return True
    return False

def update_status_with_history():
    clear_screen()
    print("\n" + "="*50)
    print("   MPCB COMPLAINT RESPONSE SYSTEM")
    print("="*50)
    
    get_statistics()
    
    complaint_id = input("\n📝 Enter Complaint ID: ")
    
    # Show current details
    if not view_complaint_details(complaint_id):
        print(f"\n❌ Complaint {complaint_id} not found!")
        input("\nPress Enter to continue...")
        return
    
    print("\n📌 Update Status to:")
    print("   1. Pending (Not yet reviewed)")
    print("   2. Under Review (Being investigated)")
    print("   3. Action Initiated (Action taken)")
    print("   4. Resolved (Problem solved)")
    print("   5. Rejected (Invalid complaint)")
    
    choice = input("\nEnter choice (1-5): ")
    
    status_map = {
        '1': 'Pending',
        '2': 'Under Review',
        '3': 'Action Initiated',
        '4': 'Resolved',
        '5': 'Rejected'
    }
    
    if choice not in status_map:
        print("❌ Invalid choice!")
        input("\nPress Enter to continue...")
        return
    
    new_status = status_map[choice]
    
    # Optional: Add response notes
    notes = input("Add response notes (optional, press Enter to skip): ")
    
    # Update database
    conn = sqlite3.connect('mpcb_grievance.db')
    cursor = conn.cursor()
    
    # Get old status
    cursor.execute('SELECT status FROM complaints WHERE id = ?', (complaint_id,))
    old_status = cursor.fetchone()[0]
    
    # Update status
    cursor.execute('UPDATE complaints SET status = ? WHERE id = ?', (new_status, complaint_id))
    conn.commit()
    conn.close()
    
    print(f"\n✅ Status updated from '{old_status}' to '{new_status}'")
    if notes:
        print(f"📝 Notes: {notes}")
    
    print("\n🔍 User can now track this complaint and see the updated status!")
    input("\nPress Enter to continue...")

def view_all_complaints():
    clear_screen()
    print("\n" + "="*90)
    print("ALL COMPLAINTS")
    print("="*90)
    
    conn = sqlite3.connect('mpcb_grievance.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id, full_name, complaint_type, status, created_at FROM complaints ORDER BY created_at DESC')
    complaints = cursor.fetchall()
    conn.close()
    
    if not complaints:
        print("\n📭 No complaints found!")
    else:
        print(f"\n{'ID':<25} {'Name':<20} {'Type':<12} {'Status':<15} {'Date'}")
        print("-"*90)
        for comp in complaints:
            date_str = comp[4][:16] if comp[4] else 'N/A'
            print(f"{comp[0]:<25} {comp[1]:<20} {comp[2]:<12} {comp[3]:<15} {date_str}")
    
    input("\nPress Enter to continue...")

def main():
    while True:
        clear_screen()
        print("\n" + "="*50)
        print("   🌿 MPCB GRIEVANCE SYSTEM")
        print("   Admin Response Panel")
        print("="*50)
        print("\n1. 📋 View All Complaints")
        print("2. ✏️ Update Complaint Status")
        print("3. 📊 View Statistics")
        print("4. 🚪 Exit")
        
        choice = input("\nEnter choice (1-4): ")
        
        if choice == '1':
            view_all_complaints()
        elif choice == '2':
            update_status_with_history()
        elif choice == '3':
            clear_screen()
            get_statistics()
            input("\nPress Enter to continue...")
        elif choice == '4':
            print("\n👋 Goodbye! Keep the environment clean! 🌿")
            break
        else:
            print("❌ Invalid choice!")
            input("\nPress Enter to continue...")

if __name__ == '__main__':
    main()