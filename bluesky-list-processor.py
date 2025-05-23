from atproto import Client, models
import asyncio
import json
import argparse
import os
from dotenv import load_dotenv
from urllib.parse import urlparse, unquote
from datetime import datetime

def convert_url_to_at_uri(url):
    """
    Convert a Bluesky web URL to an AT URI
    Examples:
    https://bsky.app/profile/did:plc:xyz/feed/abc -> at://did:plc:xyz/app.bsky.feed.generator/abc
    """
    if url.startswith('at://'):
        return url

    parsed = urlparse(url)
    if not parsed.netloc == 'bsky.app':
        raise ValueError("Not a valid Bluesky URL")

    # Extract parts from path
    parts = [p for p in parsed.path.split('/') if p]
    if len(parts) < 4 or parts[0] != 'profile':
        raise ValueError("Not a valid Bluesky feed URL")

    identifier = parts[1]
    feed_type = parts[2]  # 'feed' or 'lists'
    list_name = parts[3]

    # Determine the correct record type based on URL type
    if feed_type == 'feed':
        record_type = 'app.bsky.feed.generator'
    elif feed_type == 'lists':
        record_type = 'app.bsky.graph.list'
    else:
        raise ValueError(f"Unknown feed type: {feed_type}")

    # If it's already a DID, construct the AT URI directly
    if identifier.startswith('did:'):
        return f"at://{identifier}/{record_type}/{list_name}"
    
    return identifier, list_name, record_type

def resolve_handle_to_did(client, handle):
    """Convert a Bluesky handle to a DID - MADE SYNCHRONOUS"""
    response = client.com.atproto.identity.resolve_handle({'handle': handle})
    return response.did

def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Convert a Bluesky list or feed into a block or mute list'
    )
    parser.add_argument(
        'list_url',
        help='The URL or AT URI of the list (e.g., https://bsky.app/profile/user.bsky.social/feed/abc)'
    )
    parser.add_argument(
        '--action',
        choices=['block', 'mute'],
        required=True,
        help='Whether to block or mute users'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Only print what would be done without actually blocking/muting'
    )
    parser.add_argument(
        '--output',
        default='users_to_process.json',
        help='Output JSON file for the user list (default: users_to_process.json)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=100,
        help='Number of posts to fetch from feed (default: 100)'
    )
    return parser.parse_args()

def get_feed_users(client, uri, limit=100):
    """Get unique users from a feed - MADE SYNCHRONOUS"""
    try:
        # Get the feed posts using the correct method name
        params = models.app.bsky.feed.get_feed.Params(
            feed=uri,
            limit=limit
        )
        response = client.app.bsky.feed.get_feed(params)
        
        # Extract unique users
        users = set()
        for item in response.feed:
            if hasattr(item.post, 'author'):
                users.add((item.post.author.did, item.post.author.handle))
        
        return [{'did': did, 'handle': handle} for did, handle in users]
    except Exception as e:
        print(f"Error getting feed: {e}")
        raise

async def process_list(username, password, list_input, action, dry_run, output_file, limit):
    """
    Convert a Bluesky list into a block/mute list
    """
    print(f"Connecting to Bluesky as {username}...")
    
    # Initialize client
    client = Client()
    
    try:
        # Login
        client.login(username, password)
        print("Successfully logged in")
        
        # Convert URL to AT URI if needed
        result = convert_url_to_at_uri(list_input)
        if isinstance(result, tuple):
            # Need to resolve handle to DID
            handle, list_name, record_type = result
            print(f"Resolving handle: {handle}")
            did = resolve_handle_to_did(client, handle)  # Now synchronous
            list_uri = f"at://{did}/{record_type}/{list_name}"
            print(f"Resolved DID: {did}")
        else:
            list_uri = result
        
        print(f"Using URI: {list_uri}")
        
        # Get the list or feed content
        if 'feed.generator' in list_uri:
            print(f"Processing feed (fetching up to {limit} posts)...")
            users = get_feed_users(client, list_uri, limit)  # Now synchronous
        else:
            print("Processing list...")
            list_view = client.app.bsky.graph.get_list({'list': list_uri})
            users = [{'did': item.subject.did, 'handle': item.subject.handle} 
                    for item in list_view.items]
        
        # Save to file
        with open(output_file, 'w') as f:
            json.dump(users, f, indent=2)
        
        print(f"Found {len(users)} unique users, saved to {output_file}")
        
        if dry_run:
            print("\nDRY RUN - No actions will be taken")
            for user in users:
                print(f"Would {action} user: {user['handle']}")
            return
        
        # Process users
        print(f"\nStarting to {action} users...")
        processed = 0
        errors = 0
        for user in users:
            try:
                if action == 'block':
                    # Use the proper blocking method
                    client.app.bsky.graph.block.create(
                        repo=client.me.did,  # Use authenticated user's DID
                        record={
                            "$type": "app.bsky.graph.block",
                            "subject": user['did'],
                            "createdAt": datetime.utcnow().isoformat() + "Z"
                        }
                    )
                    print(f"Blocked {user['handle']}")
                else:
                    # Use the proper muting method
                    client.app.bsky.actor.mute_actor({
                        'actor': user['did']
                    })
                    print(f"Muted {user['handle']}")
                
                processed += 1
                # Small delay to avoid rate limits
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"Error processing {user['handle']}: {str(e)}")
                errors += 1
        
        print(f"\nCompleted: {processed} users {action}ed, {errors} errors")
                
    except Exception as e:
        print(f"Error: {str(e)}")
        return

def main():
    # Load environment variables
    load_dotenv()
    
    # Get credentials from environment
    username = os.getenv('BSKY_USERNAME')
    password = os.getenv('BSKY_PASSWORD')
    
    if not username or not password:
        print("Error: BSKY_USERNAME and BSKY_PASSWORD must be set in .env file")
        return
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Run the async function
    asyncio.run(process_list(
        username=username,
        password=password,
        list_input=args.list_url,
        action=args.action,
        dry_run=args.dry_run,
        output_file=args.output,
        limit=args.limit
    ))

if __name__ == "__main__":
    main()
