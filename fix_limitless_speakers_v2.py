#!/usr/bin/env python3
"""
Enhanced fix for Limitless speaker issues - handles all edge cases including:
1. Multiple speakers with same name (e.g., multiple "Unknown" from API)
2. Empty speaker names
3. Speakers with only IDs
4. Proper Speaker N numbering
"""

import re

def extract_speakers_from_contents_fixed(log):
    """
    Fixed version that properly handles all speaker edge cases.
    """
    speakers = []
    contents = log.get('contents', [])
    
    speaker_id_mapping = {}  # Map speaker IDs to Speaker N names
    speaker_id_to_info = {}  # Track all info about each speaker ID
    unrecognized_speaker_counter = 0
    user_detected = False
    
    # First pass: collect all unique speaker IDs and their names
    for content in contents:
        speaker_name = content.get('speakerName', '').strip()
        speaker_id = content.get('speakerIdentifier', '').strip()
        
        if not speaker_id:
            continue
            
        # Store speaker info by ID
        if speaker_id not in speaker_id_to_info:
            speaker_id_to_info[speaker_id] = {
                'names': set(),
                'is_user': speaker_id == 'user'
            }
        
        if speaker_name:
            speaker_id_to_info[speaker_id]['names'].add(speaker_name)
    
    # Second pass: create speaker entries
    for speaker_id, info in speaker_id_to_info.items():
        names = info['names']
        is_user = info['is_user']
        
        if is_user:
            # Handle primary user
            speakers.append({
                'name': 'You',
                'context': 'Primary user (speaker)',
                'role': 'primary_user',
                'speaker_id': speaker_id
            })
            user_detected = True
        elif names:
            # Check if any of the names are problematic
            valid_names = [n for n in names if n and 
                          n.lower() not in ['unknown', 'unknown speaker', 'unidentified', '']]
            
            if valid_names:
                # Use the first valid name
                speaker_name = sorted(valid_names)[0]  # Consistent selection
                speakers.append({
                    'name': speaker_name,
                    'context': 'Identified speaker in conversation',
                    'role': 'participant',
                    'speaker_id': speaker_id
                })
            else:
                # All names are problematic - assign Speaker N
                speaker_n_name = f"Speaker {unrecognized_speaker_counter}"
                speaker_id_mapping[speaker_id] = speaker_n_name
                
                speakers.append({
                    'name': speaker_n_name,
                    'context': 'Unrecognized speaker in conversation',
                    'role': 'participant',
                    'speaker_id': speaker_id
                })
                unrecognized_speaker_counter += 1
        else:
            # No name at all - assign Speaker N
            speaker_n_name = f"Speaker {unrecognized_speaker_counter}"
            speaker_id_mapping[speaker_id] = speaker_n_name
            
            speakers.append({
                'name': speaker_n_name,
                'context': 'Unrecognized speaker in conversation',
                'role': 'participant',
                'speaker_id': speaker_id
            })
            unrecognized_speaker_counter += 1
    
    # Handle contents without any speaker ID (edge case)
    has_unattributed_content = any(
        not content.get('speakerIdentifier', '').strip() 
        for content in contents 
        if content.get('content', '').strip()
    )
    
    if has_unattributed_content and not user_detected:
        # Add a generic speaker for unattributed content
        speakers.append({
            'name': f"Speaker {unrecognized_speaker_counter}",
            'context': 'Unattributed content in conversation',
            'role': 'participant'
        })
    
    # Final fallback: ensure at least one speaker
    if not speakers:
        speakers.append({
            'name': 'You',
            'context': 'Primary user (assumed speaker)',
            'role': 'primary_user'
        })
    
    # Store speaker mapping for consistent naming throughout transcript
    log['_speaker_mapping'] = speaker_id_mapping
    
    return speakers


def build_transcript_with_proper_speakers(log):
    """
    Build transcript with proper speaker attribution, never using "Unknown".
    """
    transcript_parts = []
    contents = log.get('contents', [])
    speaker_id_mapping = log.get('_speaker_mapping', {})
    
    for content in contents:
        speaker_name = content.get('speakerName', '').strip()
        speaker_id = content.get('speakerIdentifier', '').strip()
        content_text = content.get('content', '').strip()
        
        if not content_text:
            continue
            
        # Determine the speaker label
        speaker_label = None
        
        if speaker_id == 'user':
            speaker_label = "You"
        elif speaker_name and speaker_name.lower() not in ['unknown', 'unknown speaker', 'unidentified', '']:
            # Valid speaker name from API
            speaker_label = speaker_name
        elif speaker_id and speaker_id in speaker_id_mapping:
            # Use mapped Speaker N name
            speaker_label = speaker_id_mapping[speaker_id]
        elif speaker_id:
            # Unmapped speaker ID - this shouldn't happen if extract_speakers was called first
            # But handle it gracefully
            speaker_label = "Speaker"
        else:
            # No speaker info at all
            speaker_label = "Speaker"
        
        transcript_parts.append(f"{speaker_label}: {content_text}")
    
    return '\n'.join(transcript_parts)


# Test the fix
if __name__ == "__main__":
    # Test case: Multiple "Unknown" speakers from API
    test_log = {
        'id': 'test123',
        'contents': [
            {'speakerIdentifier': 'user', 'speakerName': '', 'content': 'Hello everyone'},
            {'speakerIdentifier': 'spk1', 'speakerName': 'Unknown', 'content': 'Hi there'},
            {'speakerIdentifier': 'spk2', 'speakerName': 'Unknown', 'content': 'Good morning'},
            {'speakerIdentifier': 'spk3', 'speakerName': 'Unknown', 'content': 'How are you?'},
            {'speakerIdentifier': 'spk1', 'speakerName': 'Unknown', 'content': 'I am fine'},
            {'speakerIdentifier': 'spk4', 'speakerName': 'John', 'content': 'Great to hear'},
            {'speakerIdentifier': '', 'speakerName': '', 'content': 'Random comment'},
        ]
    }
    
    print("Testing speaker extraction fix...")
    speakers = extract_speakers_from_contents_fixed(test_log)
    
    print("\nExtracted speakers:")
    for speaker in speakers:
        print(f"  - {speaker['name']}: {speaker['context']} (ID: {speaker.get('speaker_id', 'none')})")
    
    print("\nSpeaker ID mapping:")
    print(f"  {test_log.get('_speaker_mapping', {})}")
    
    print("\nBuilding transcript:")
    transcript = build_transcript_with_proper_speakers(test_log)
    print(transcript)