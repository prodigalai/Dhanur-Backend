#!/bin/bash

echo "🚀 Deploying datetime fixes to Heroku..."

# Add all changes
git add .

# Commit changes
git commit -m "Fix datetime timezone issues - replace utcnow() with timezone-aware datetime"

# Push to Heroku
git push heroku main

echo "✅ Deployment complete! Check Heroku logs for any issues."
