# GitHub Actions Workflows

## JTI Cleanup Job

Automated job to clean up old JWT Token Identifiers (JTI) from the `used_jti` table to prevent database bloat.

### Schedule
- **Runs daily at 02:00 WIB (19:00 UTC)**
- Can also be triggered manually via GitHub UI

### Setup

#### 1. Configure GitHub Secrets

Go to your repository: **Settings → Secrets and variables → Actions → New repository secret**

Add the following secrets:

| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `API_BASE_URL` | Base URL of your deployed API | `https://api.example.com` |
| `ADMIN_TOKEN` | Admin JWT token from Atlas SSO | `eyJhbGciOiJIUzI1NiIsInR5cCI...` |

#### 2. Get Admin Token

To obtain the `ADMIN_TOKEN`:

1. Login to your HRIS application as an admin user (role level >= 50)
2. Open browser DevTools → Application/Storage → Cookies or Local Storage
3. Copy the JWT token value
4. Add it to GitHub Secrets as `ADMIN_TOKEN`

**Security Note**: This token should be long-lived or refreshed periodically. Consider using a service account with limited permissions.

#### 3. Test the Workflow

You can manually trigger the workflow to test:

1. Go to **Actions** tab in GitHub
2. Select **JTI Cleanup Job**
3. Click **Run workflow**
4. Monitor the logs

### What It Does

The workflow:
1. Calls `POST /api/v1/maintenance/cleanup-jti?days_old=7`
2. Deletes JTI records older than 7 days
3. Logs the number of deleted records
4. Fails if the API returns an error

### Monitoring

- Check **Actions** tab for workflow runs
- Failed runs will show red X and error details
- Success runs show number of records deleted

### Troubleshooting

**401 Unauthorized**
- Admin token expired or invalid
- Update the `ADMIN_TOKEN` secret

**404 Not Found**
- Check `API_BASE_URL` is correct
- Ensure `/api/v1/maintenance/cleanup-jti` endpoint exists

**500 Internal Server Error**
- Check API logs
- Verify database connection
- Check that `hris.used_jti` table exists

### Manual Cleanup

If you need to run cleanup manually:

```bash
curl -X POST "https://api.example.com/api/v1/maintenance/cleanup-jti?days_old=7" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json"
```

### Adjusting Schedule

To change the cleanup schedule, edit `.github/workflows/jti-cleanup.yml`:

```yaml
schedule:
  - cron: '0 19 * * *'  # 02:00 WIB daily
```

Cron format: `minute hour day month weekday` (in UTC)

Examples:
- `0 19 * * *` - Daily at 02:00 WIB
- `0 */12 * * *` - Every 12 hours
- `0 19 * * 0` - Every Sunday at 02:00 WIB
