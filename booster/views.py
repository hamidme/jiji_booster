import json
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
import anthropic
from decouple import config


def pwa_manifest(request):
    return JsonResponse({
        "name": "Jiji Booster",
        "short_name": "JijiBoost",
        "description": "AI-powered listings for Nigerian sellers on Jiji.ng",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#ffffff",
        "theme_color": "#00a651",
        "icons": [
            {
                "src": "/static/booster/icons/icon-192.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": "/static/booster/icons/icon-512.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable",
            },
        ],
    }, content_type='application/manifest+json')


_SW_JS = """\
const CACHE = 'jiji-booster-v2';

// Install: skip waiting immediately — no network calls that could fail
self.addEventListener('install', e => {
  e.waitUntil(self.skipWaiting());
});

// Activate: clear old caches, claim all clients
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// Fetch: network-first, cache lazily; skip POST
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    fetch(e.request)
      .then(res => {
        const clone = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, clone));
        return res;
      })
      .catch(() => caches.match(e.request))
  );
});
"""


def service_worker(request):
    res = HttpResponse(_SW_JS, content_type='application/javascript')
    res['Cache-Control'] = 'no-cache'
    return res

SYSTEM_PROMPT = """You are an expert Nigerian e-commerce copywriter and digital marketing specialist
with deep knowledge of Jiji.ng marketplace. You help Nigerian sellers write compelling, optimized
product listings that sell fast.

Your listings:
- Use professional, relatable Nigerian English
- Include keywords Nigerians actually search for on Jiji.ng
- Create urgency and trust appropriate for the Nigerian market
- Keep titles under 70 characters but keyword-rich and compelling
- Descriptions address key buyer concerns: authenticity, condition, price fairness, delivery options
- WhatsApp messages feel personal and prompt quick buyer replies
- Facebook Marketplace posts are slightly more formal than WhatsApp but still conversational: include price, location, condition, and a clear call to action
- SEO keywords reflect real Nigerian search behavior on Jiji.ng"""

CONDITION_LABELS = {
    'brand_new': 'Brand New',
    'foreign_used': 'Foreign/UK Used',
    'locally_used': 'Locally Used (Neat)',
    'refurbished': 'Refurbished/Grade A',
}

LISTING_SCHEMA = {
    "type": "object",
    "properties": {
        "listing_title": {
            "type": "string",
            "description": "Optimized Jiji.ng listing title, max 70 characters"
        },
        "listing_description": {
            "type": "string",
            "description": "Full listing description, 200-400 words"
        },
        "whatsapp_message": {
            "type": "string",
            "description": "WhatsApp promotional message, 100-200 words"
        },
        "facebook_post": {
            "type": "string",
            "description": "Facebook Marketplace post, 100-200 words, slightly more formal than WhatsApp but still conversational, includes price, location, condition, and call to action"
        },
        "seo_keywords": {
            "type": "array",
            "items": {"type": "string"},
            "description": "8-12 SEO keywords for Jiji.ng"
        }
    },
    "required": ["listing_title", "listing_description", "whatsapp_message", "facebook_post", "seo_keywords"],
    "additionalProperties": False
}


def index(request):
    result = None
    error = None
    form_data = {}

    if request.method == 'POST':
        form_data = {
            'product_name': request.POST.get('product_name', '').strip(),
            'key_features': request.POST.get('key_features', '').strip(),
            'price': request.POST.get('price', '').strip(),
            'condition': request.POST.get('condition', 'brand_new'),
            'location': request.POST.get('location', '').strip(),
        }

        missing = [k for k, v in form_data.items() if not v]
        if missing:
            error = "Please fill in all required fields."
        else:
            condition_label = CONDITION_LABELS.get(form_data['condition'], form_data['condition'])
            user_prompt = f"""Create an optimized Jiji.ng listing for this product:

Product Name: {form_data['product_name']}
Key Features: {form_data['key_features']}
Asking Price: ₦{form_data['price']}
Condition: {condition_label}
Seller Location: {form_data['location']}

Generate:
1. listing_title — Compelling, keyword-rich title (max 70 characters)
2. listing_description — Detailed description (200-400 words): product details, condition, features, why it's a great deal, delivery/pickup info placeholder, and call-to-action
3. whatsapp_message — Persuasive WhatsApp message (100-200 words) to share in buyer groups: personal tone, create urgency
4. facebook_post — Facebook Marketplace post (100-200 words): slightly more formal than WhatsApp but still conversational; clearly state price (₦{form_data['price']}), location ({form_data['location']}), condition ({condition_label}), key highlights, and end with a call to action (DM or comment)
5. seo_keywords — List of 8-12 search terms Nigerians use on Jiji.ng for this product"""

            try:
                client = anthropic.Anthropic(api_key=config('ANTHROPIC_API_KEY'))
                response = client.messages.create(
                    model="claude-opus-4-7",
                    max_tokens=2560,
                    system=[{
                            "type": "text",
                            "text": SYSTEM_PROMPT,
                            "cache_control": {"type": "ephemeral"},
                        }],
                    messages=[{"role": "user", "content": user_prompt}],
                    output_config={
                        "format": {
                            "type": "json_schema",
                            "schema": LISTING_SCHEMA
                        }
                    }
                )
                text_content = next(b.text for b in response.content if b.type == "text")
                result = json.loads(text_content)
            except anthropic.APIStatusError as e:
                error = f"API Error: {e.message}"
            except anthropic.APIConnectionError:
                error = "Connection failed. Please check your internet and try again."
            except Exception as e:
                error = f"Error: {str(e)}"

    return render(request, 'booster/index.html', {
        'result': result,
        'error': error,
        'form_data': form_data,
    })
