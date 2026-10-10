# 🛍️ SaiDeals — Smart Savings Plus

A premium multi-store affiliate deal website that aggregates products from Amazon, Flipkart, Meesho, and Ajio. Built with pure HTML, CSS, and JavaScript — no frameworks, no backend, 100% free to host.

---

## 📁 File List

| File | Purpose |
|------|---------|
| index.html | Public storefront homepage |
| style.css | Storefront styling (premium Flipkart-style UI) |
| script.js | Storefront logic (search, filter, wishlist, recommendations) |
| data.json | Fallback product data |
| sd-console.html | Private admin panel (only you know this URL) |
| admin.css | Admin panel styling |
| admin.js | Admin panel logic (login, add/edit/delete, bulk import, settings) |
| bookmarklet.txt | Browser bookmarklet to grab product data |
| README.md | This documentation file |

---

## 🚀 Deployment Guide (GitHub + Cloudflare Pages)

Step 1: Create GitHub Account
- Go to github.com → Sign up (free)
- Verify your email

Step 2: Create Repository
- Click "New repository"
- Repository name: saideals
- Set to Public (required for free Cloudflare Pages)
- Click "Create repository"

Step 3: Upload Files
- Click "Add file" → "Create new file"
- Add each of the 9 files one by one
- Paste the code in each file
- Commit with a descriptive message

Step 4: Deploy on Cloudflare Pages
- Go to dash.cloudflare.com → Sign up (free)
- Left menu → Workers & Pages → Create → Pages → Connect to Git
- Authorize GitHub → Select saideals repository
- Build settings:
  - Framework preset: None
  - Build command: (leave empty)
  - Build output directory: /
- Click "Save and Deploy"
- Wait 1-2 minutes → Your site is live at saideals.pages.dev

Step 5: Custom Domain (Optional)
- Buy domain from namecheap.com or godaddy.com
- Cloudflare Pages → Custom domains → Set up a domain
- Follow DNS instructions
- Wait 5-30 minutes for propagation

---

## 📊 Google Sheet Setup (For All Visitors to See Products)

Why use Google Sheet?
The admin panel saves products in localStorage — which means only YOUR browser sees them. To show products to ALL visitors, use Google Sheet as your data source.

Step 1: Create Google Sheet
- Go to sheets.google.com → Blank spreadsheet
- Name it: SaiDeals Products
- In row 1, add these headers exactly:
  id | name | price | originalPrice | rating | reviews | store | category | image | link | badge

Step 2: Add Products (Row 2 onwards)
Example row:
1 | boAt Airdopes 141 | 499 | 1299 | 4.3 | 12450 | Flipkart | gadget | https://i.ibb.co/xxx.jpg | https://fkrt.it/xxx | Bestseller

Step 3: Share Sheet Publicly
- Click "Share" button
- Change to "Anyone with the link"
- Set permission to "Viewer"
- Click "Done"

Step 4: Get Sheet ID
- Your URL looks like: https://docs.google.com/spreadsheets/d/1ABC...XYZ/edit
- The 1ABC...XYZ part is your SHEET_ID

Step 5: Update script.js
- Open script.js in any text editor
- Find: YOUR_SHEET_ID
- Replace with your actual Sheet ID
- Save and re-upload to GitHub

Step 6: Test
- Open in browser: https://opensheet.elk.sh/YOUR_SHEET_ID/Sheet1
- You should see JSON data
- If it works, your site will load from Google Sheet

---

## 🔐 Admin Panel Access

URL: https://yoursite.com/sd-console.html
IMPORTANT: NEVER share this URL publicly. Bookmark it in your browser only.

Default Login:
- Username: admin
- Password: saideals2026

Change Password:
- Open admin.js in a text editor
- Find at the top:
  const DEFAULT_USER = "admin";
  const DEFAULT_PASS = "saideals2026";
- Change to your own strong password
- Save and re-upload to GitHub
- Alternatively, log in and use Settings → Change Password (saved in your browser only)

---

## 🛡️ Cloudflare Access (REAL Security)

Why?
Browser-based login is not real security. Anyone who opens the page source can see the password. For real protection, use Cloudflare Access.

Setup Steps:
1. Cloudflare Dashboard → Security → Access → Applications
2. Click "Add an application" → "Self-hosted"
3. Application name: SD Console
4. Session duration: 24 hours
5. Add public hostname:
   - Subdomain: (leave empty)
   - Domain: yoursite.com
   - Path: sd-console.html
6. Click "Next"
7. Policy name: Only Me
8. Action: Allow
9. Include → Emails → Enter your email
10. Click "Next" → "Add application"
11. Choose login method: One-time PIN
12. Save

Result: Opening sd-console.html now requires email OTP. Free for up to 50 users.

---

## 🔖 Bookmarklet Installation

Desktop (Chrome/Edge):
1. Press Ctrl + Shift + B to show Bookmarks Bar
2. Right-click the bar → "Add page"
3. Name: SaiDeals Grabber
4. URL: Paste the entire code from bookmarklet.txt
5. Click "Save"

Mobile (Chrome):
1. Open any product page
2. In the URL bar, type: javascript:
3. Paste the bookmarklet code after it
4. Press Enter

How to Use:
1. Open any product page on Amazon / Flipkart / Meesho / Ajio
2. Click the "SaiDeals Grabber" bookmark
3. A modal appears with product data in JSON
4. Click "Copy JSON" or "Open Admin"
5. If using "Open Admin" → data pre-fills in sd-console.html

---

## 📦 Adding Products (3 Methods)

Method 1: Admin Panel (Easiest for You)
1. Open sd-console.html → Login
2. Click "Add Product"
3. Fill all fields (name, price, image URL, affiliate link, etc.)
4. Click "Save"
5. Product appears instantly in your browser
Note: Only YOU see it (localStorage)

Method 2: Google Sheet (Best for All Visitors)
1. Open your Google Sheet
2. Add a new row with product data
3. Save (auto-saves)
4. Site updates in 1-2 minutes

Method 3: Bulk Import (For Many Products)
1. Open sd-console.html → Bulk Import
2. Paste JSON array:
   [
     {"id":1,"name":"Product 1","price":499,"store":"Amazon","link":"https://..."},
     {"id":2,"name":"Product 2","price":799,"store":"Flipkart","link":"https://..."}
   ]
3. Click "Validate" → then "Import"
4. All products added at once

---

## ⚠️ Important Warnings

1. No Paid Ads
- DO NOT run Google Ads or Facebook Ads pointing to affiliate links
- Flipkart/Amazon will BAN your affiliate account permanently
- Only use organic methods: social media, SEO, Pinterest, WhatsApp

2. No Logo Copying
- Do not copy Amazon/Flipkart/Meesho logos
- Use text badges: "Available on Amazon"
- Use your OWN brand name and logo

3. Affiliate Disclosure
- Required by law in most countries
- Already included in footer of index.html
- Never remove it

4. Read Store Terms
- Each affiliate program has its own rules
- Read them carefully before promoting
- Violations = permanent ban + commission loss

5. Self-Purchases Don't Count
- Buying through your own link = no commission (detected by same IP/device)
- Ask friends/family to purchase instead

6. Cookie Duration
- Amazon: 24 hours
- Flipkart: 7 days
- Meesho: 15 days
- Ajio: 30 days

---

## 🐛 Troubleshooting

Site shows blank page
- Open browser console (F12) → check for errors
- Make sure data.json is in the same folder
- If using Google Sheet, verify the opensheet URL works

Products not showing from Google Sheet
- Check Sheet is shared as "Anyone with link can view"
- Verify YOUR_SHEET_ID in script.js is correct
- Test: open https://opensheet.elk.sh/YOUR_SHEET_ID/Sheet1

Admin panel login fails
- Default: admin / saideals2026
- Clear browser cache: Ctrl + Shift + Delete
- Check admin.js DEFAULT_USER and DEFAULT_PASS

Bookmarklet doesn't work
- Site markup changed → send me the URL, I'll update selectors
- Check browser console (F12) for errors
- Try on a different product page

Images not loading
- Upload images to imgbb.com (free)
- Use direct image URL (ends in .jpg / .png / .webp)
- Avoid Google Drive links (they don't work as direct images)

Site slow
- Optimize images: tinypng.com
- Use lazy loading: <img loading="lazy">
- Keep data.json under 100 products

---

## 📈 Growth Tips

Daily Routine (5 minutes)
1. Morning: Find 5 trending deals on Amazon/Flipkart
2. Use bookmarklet → grab data
3. Add to Admin Panel or Google Sheet
4. Evening: Share on WhatsApp/Instagram

Traffic Sources (Free)
- Pinterest: Post product images with site link (best long-term)
- Instagram Reels: 15-30 sec product videos
- YouTube Shorts: Quick reviews
- WhatsApp Groups: Share deals daily
- Quora/Reddit: Answer questions + link
- SEO Blog: "Best earbuds under 500" articles

Commission Estimate
- 100 visitors/day → ~Rs.500-1500/month
- 500 visitors/day → ~Rs.3000-8000/month
- 1000 visitors/day → ~Rs.7000-15000/month
(Depends on niche, product prices, and conversion rate)

---

## 📞 Support

If you find bugs or need help:
1. Check this README first
2. Test in browser console (F12)
3. Note the exact error message
4. Ask in the community

---

## 📜 License

Free to use for personal affiliate business.
Not for resale.

---

## 🎉 You're All Set!

Your SaiDeals affiliate site is now:
- Live on the internet
- Secured with Cloudflare Access
- Connected to Google Sheet
- Ready to earn commission

Start adding products, share on social media, and watch the commissions roll in!

---

Last updated: 2026
