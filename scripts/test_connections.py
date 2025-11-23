#!/usr/bin/env python3
"""
Test all connections are working.
Everyone runs this after setup.
"""
import json
import os
from dotenv import load_dotenv

def test_all_connections():
    print("🧪 Testing all connections...\n")
    
    # Load environment
    load_dotenv('config/.env')
    
    results = {
        "secrets_file": False,
        "env_file": False,
        "snowflake": False,
        "aws_s3": False,
        "openai": False
    }
    
    # Test 1: secrets.json exists
    print("1️⃣ Checking secrets.json...")
    if os.path.exists('secrets.json'):
        print("   ✅ secrets.json found")
        results["secrets_file"] = True
    else:
        print("   ❌ secrets.json not found")
    
    # Test 2: .env file exists
    print("\n2️⃣ Checking config/.env...")
    if os.path.exists('config/.env'):
        print("   ✅ config/.env found")
        results["env_file"] = True
    else:
        print("   ❌ config/.env not found")
    
    # Test 3: Snowflake connection
    print("\n3️⃣ Testing Snowflake connection...")
    try:
        import snowflake.connector
        
        conn = snowflake.connector.connect(
            account=os.getenv('SNOWFLAKE_ACCOUNT'),
            user=os.getenv('SNOWFLAKE_USER'),
            password=os.getenv('SNOWFLAKE_PASSWORD'),
            warehouse=os.getenv('SNOWFLAKE_WAREHOUSE')
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT CURRENT_USER(), CURRENT_ACCOUNT()")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        print(f"   ✅ Connected as: {result[0]}")
        print(f"   ✅ Account: {result[1]}")
        results["snowflake"] = True
    except ImportError:
        print("   ⚠️  snowflake-connector-python not installed")
        print("   Run: pip install snowflake-connector-python")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
    
    # Test 4: AWS S3
    print("\n4️⃣ Testing AWS S3 access...")
    try:
        import boto3
        
        s3 = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION')
        )
        
        bucket = os.getenv('AWS_S3_BUCKET')
        s3.head_bucket(Bucket=bucket)
        
        print(f"   ✅ Can access bucket: {bucket}")
        results["aws_s3"] = True
    except ImportError:
        print("   ⚠️  boto3 not installed")
        print("   Run: pip install boto3")
    except Exception as e:
        print(f"   ❌ S3 access failed: {e}")
    
    # Test 5: OpenAI API (optional)
    print("\n5️⃣ Testing OpenAI API...")
    openai_key = os.getenv('OPENAI_API_KEY')
    if openai_key and openai_key != 'sk-...':
        try:
            import openai
            openai.api_key = openai_key
            # Simple test - just check key format
            if openai_key.startswith('sk-'):
                print(f"   ✅ API key configured (starts with sk-)")
                results["openai"] = True
            else:
                print("   ⚠️  API key format looks wrong")
        except ImportError:
            print("   ⚠️  openai package not installed")
            print("   Run: pip install openai")
        except Exception as e:
            print(f"   ❌ OpenAI test failed: {e}")
    else:
        print("   ⚠️  OpenAI API key not configured (optional)")
    
    # Summary
    print("\n" + "="*50)
    print("📊 SUMMARY")
    print("="*50)
    
    passed = sum(results.values())
    total = len(results)
    
    for test, result in results.items():
        status = "✅" if result else "❌"
        print(f"{status} {test}")
    
    print(f"\n🎯 Passed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 All tests passed! Ready for Day 1!")
    elif passed >= 3:
        print("\n👍 Core tests passed! You can start Day 1")
    else:
        print("\n⚠️  Need to fix some issues before Day 1")
    
    return results

if __name__ == "__main__":
    test_all_connections()