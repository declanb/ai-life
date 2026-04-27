"""Free day planner service.

Generates shopping and activity recommendations when the user has free time
during a work trip. Combines trip data, calendar gaps, location context, and
user preferences to surface decisive, high-value options.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from app.schemas.free_day import (
    ActivityCategory,
    ActivityRecommendation,
    FreeDayContext,
    FreeDayPlan,
    PriceLevel,
    ShoppingCategory,
    ShoppingRecommendation,
)
from app.schemas.trip import Trip


class FreeDayPlannerService:
    """
    Generates free-day plans for work trips.
    
    Current implementation uses curated recommendations per city.
    Future: integrate Google Places, weather APIs, user preference store.
    """

    # Curated city data — in production, this would be a database + live APIs
    CITY_DATA = {
        "Munich": {
            "shopping": [
                {
                    "title": "Uniqlo Munich (Kaufingerstraße)",
                    "category": ShoppingCategory.WARDROBE,
                    "description": "Restock travel staples — AIRism underwear, Heattech layers, packable down",
                    "price_estimate": "€10-60/item",
                    "price_level": PriceLevel.BUDGET,
                    "location": "Kaufingerstraße 1-5",
                    "address": "Kaufingerstraße 1-5, 80331 München",
                    "opening_hours": "Mon-Sat 10:00-20:00",
                    "distance_from_hotel": "5 min walk from Courtyard Marriott City Centre",
                    "url": "https://www.uniqlo.com/de/de/store/munich-kaufingerstrasse",
                    "confidence_score": 0.9,
                    "reasoning": "Reliable for travel wardrobe gaps — same sizing you know, good for socks/t-shirts/base layers if you packed light. Walking distance from your hotel.",
                },
                {
                    "title": "Globetrotter (outdoor specialist)",
                    "category": ShoppingCategory.LOCAL_SPECIALTY,
                    "description": "Premium outdoor gear — Arc'teryx, Patagonia, Fjällräven at better prices than UK",
                    "price_estimate": "€80-300",
                    "price_level": PriceLevel.PREMIUM,
                    "location": "Isartorplatz 8",
                    "address": "Isartorplatz 8, 80331 München",
                    "opening_hours": "Mon-Sat 10:00-20:00",
                    "distance_from_hotel": "10 min walk from Courtyard Marriott or 5 min Uber (€5-7)",
                    "url": "https://www.globetrotter.de/filialen/muenchen/",
                    "confidence_score": 0.85,
                    "reasoning": "Germany prices ~15-20% below UK for Arc'teryx, Patagonia. Worth it if you've been eyeing a shell jacket or pack. Easy walk or quick Uber.",
                },
                {
                    "title": "Saturn (electronics)",
                    "category": ShoppingCategory.ELECTRONICS,
                    "description": "USB-C cables, adaptors, power banks, camera SD cards — emergency tech supplies",
                    "price_estimate": "€5-50",
                    "price_level": PriceLevel.BUDGET,
                    "location": "Kaufingerstraße 15 (opposite Uniqlo)",
                    "address": "Kaufingerstraße 15, 80331 München",
                    "opening_hours": "Mon-Sat 10:00-20:00",
                    "distance_from_hotel": "5 min walk from Courtyard Marriott",
                    "url": "https://www.saturn.de/de/store/munich-kaufingerstrasse",
                    "confidence_score": 0.8,
                    "reasoning": "If you forgot a cable or your charger is failing. Reliable chain, immediate stock. Right by your hotel.",
                },
                {
                    "title": "Viktualienmarkt gift stalls",
                    "category": ShoppingCategory.GIFTS,
                    "description": "Gourmet gifts — Bavarian mustard, smoked sausages, honey, cheese, beer steins",
                    "price_estimate": "€5-30/item",
                    "price_level": PriceLevel.MODERATE,
                    "location": "Viktualienmarkt (outdoor market)",
                    "address": "Viktualienmarkt 3, 80331 München",
                    "opening_hours": "Mon-Sat 08:00-18:00 (closes early Sat)",
                    "distance_from_hotel": "8 min walk from Courtyard Marriott",
                    "url": "https://www.muenchen.de/en/locations/viktualienmarkt",
                    "confidence_score": 0.75,
                    "reasoning": "Authentic food gifts that travel well. Better than airport. Avoid tourist tat stalls. Easy walk from your hotel.",
                },
            ],
            "activities": [
                {
                    "title": "Allianz Arena VIP Tour",
                    "category": ActivityCategory.SIGHTSEEING,
                    "description": "Exclusive behind-the-scenes tour — players' tunnel, locker rooms, press room, pitch-side access. FC Bayern history.",
                    "price_estimate": "€35-45/person VIP tour",
                    "price_level": PriceLevel.PREMIUM,
                    "duration": "1.5-2 hours",
                    "location": "Allianz Arena",
                    "address": "Werner-Heisenberg-Allee 25, 80939 München",
                    "distance_from_hotel": "20 min Uber Black from Courtyard Marriott (€25-35)",
                    "url": "https://allianz-arena.com/en/tours",
                    "booking_required": True,
                    "best_time": "Morning or early afternoon — check match schedule",
                    "confidence_score": 0.9,
                    "reasoning": "Premium experience at one of Europe's most iconic stadiums. VIP tour is much better than standard. Book ahead. Uber Black makes the journey comfortable.",
                },
                {
                    "title": "Käfer-Schänke lunch (Michelin)",
                    "category": ActivityCategory.FOOD,
                    "description": "Michelin-starred Bavarian fine dining on Prinzregentenstraße. Modern takes on classics — schnitzel, venison, local fish.",
                    "price_estimate": "€80-120/person with wine",
                    "price_level": PriceLevel.PREMIUM,
                    "duration": "2-2.5 hours",
                    "location": "Prinzregentenstraße 73",
                    "address": "Prinzregentenstraße 73, 81675 München",
                    "distance_from_hotel": "10 min Uber Black (€12-18)",
                    "url": "https://www.feinkost-kaefer.de/en/schwabing",
                    "booking_required": True,
                    "best_time": "Lunch (12:30-2pm) — book 1-2 days ahead",
                    "confidence_score": 0.92,
                    "reasoning": "Corporate card-friendly, relaxed Michelin star. Bavarian soul with refinement. Easier to book than Tantris, better value than hotel restaurants.",
                },
                {
                    "title": "Atelier lunch (3 Michelin stars)",
                    "category": ActivityCategory.FOOD,
                    "description": "Jan Hartwig's 3-star restaurant. 6-course lunch menu, impeccable technique, theatrical presentation.",
                    "price_estimate": "€195/person (lunch menu), €250+ with wine pairing",
                    "price_level": PriceLevel.PREMIUM,
                    "duration": "3-3.5 hours",
                    "location": "Hotel Bayerischer Hof",
                    "address": "Promenadeplatz 2-6, 80333 München",
                    "distance_from_hotel": "5 min Uber or 12 min walk",
                    "url": "https://www.atelier.de/en",
                    "booking_required": True,
                    "best_time": "Lunch (12:30pm) — book 2-4 weeks ahead",
                    "confidence_score": 0.85,
                    "reasoning": "If you want the full fine-dining experience and have 3+ hours. Lunch is better value than dinner. Corporate Amex justified — this is a special occasion.",
                },
                {
                    "title": "Englischer Garten morning walk & coffee",
                    "category": ActivityCategory.OUTDOOR,
                    "description": "Europe's largest urban park — walk to Chinese Tower beer garden, watch river surfers at Eisbach",
                    "price_estimate": "Free (€4-6 for coffee)",
                    "price_level": PriceLevel.BUDGET,
                    "duration": "1-2 hours",
                    "location": "Englischer Garten",
                    "address": "Entry at Haus der Kunst or Münchner Freiheit U-Bahn",
                    "distance_from_hotel": "10 min Uber from Courtyard Marriott City Centre (€8-12)",
                    "url": "https://www.muenchen.de/en/locations/englischer-garten",
                    "booking_required": False,
                    "best_time": "Morning (8-11am) — quiet, good light, locals jogging",
                    "confidence_score": 0.95,
                    "reasoning": "Classic Munich experience, free, flexible duration. Essential if it's your first visit and weather's decent. Quick Uber from your hotel.",
                },
                {
                    "title": "Deutsches Museum",
                    "category": ActivityCategory.CULTURE,
                    "description": "World's largest science/tech museum — aviation, space, transport, energy. Could spend all day.",
                    "price_estimate": "€15 entry",
                    "price_level": PriceLevel.MODERATE,
                    "duration": "3-5 hours (or full day)",
                    "location": "Museumsinsel 1",
                    "address": "Museumsinsel 1, 80538 München",
                    "distance_from_hotel": "8 min Uber from Courtyard Marriott (€6-10)",
                    "url": "https://www.deutsches-museum.de/en",
                    "booking_required": False,
                    "best_time": "Morning (opens 9am) — less crowded",
                    "confidence_score": 0.9,
                    "reasoning": "If you're into engineering/tech, this is world-class. Skip if you're not interested — it's huge and intense. Your hotel is very close, easy Uber.",
                },
                {
                    "title": "Lunch at Viktualienmarkt",
                    "category": ActivityCategory.FOOD,
                    "description": "Outdoor food market — grab sausages, cheese, bread, beer and sit at communal tables. Peak local vibe.",
                    "price_estimate": "€10-18/person",
                    "price_level": PriceLevel.BUDGET,
                    "duration": "1 hour",
                    "location": "Viktualienmarkt",
                    "address": "Viktualienmarkt 3, 80331 München",
                    "distance_from_hotel": "8 min walk from Courtyard Marriott",
                    "url": "https://www.muenchen.de/en/locations/viktualienmarkt",
                    "booking_required": False,
                    "best_time": "Lunch (12-2pm) — full energy, all stalls open",
                    "confidence_score": 0.92,
                    "reasoning": "Authentic, fast, cheap, outdoors. Better than tourist restaurants around Marienplatz. Walking distance from your hotel.",
                },
                {
                    "title": "BMW Welt & Museum",
                    "category": ActivityCategory.SIGHTSEEING,
                    "description": "Futuristic showroom (Welt, free) + 100 years of BMW history in the museum. Latest M cars, concept vehicles, heritage collection.",
                    "price_estimate": "Welt free, Museum €10 (or €19 combined with factory tour)",
                    "price_level": PriceLevel.PREMIUM,
                    "duration": "2-4 hours (add 2.5h for factory tour)",
                    "location": "Olympic Park area",
                    "address": "Am Olympiapark 2, 80809 München",
                    "distance_from_hotel": "15 min Uber Black from Courtyard Marriott (€22-30)",
                    "url": "https://www.bmw-welt.com/en.html",
                    "booking_required": True,
                    "best_time": "Mid-morning (10am) — book factory tour 2-3 weeks ahead if interested",
                    "confidence_score": 0.88,
                    "reasoning": "Combine Allianz Arena + BMW Welt in one trip (same area). Museum is excellent if you're into cars. Factory tour adds 2.5h but shows production line — book ahead. Uber Black keeps it comfortable.",
                },
                {
                    "title": "Neuschwanstein Castle day trip",
                    "category": ActivityCategory.DAY_TRIP,
                    "description": "Iconic fairytale castle, 2h each way by train. Book morning slot, back by 6pm.",
                    "price_estimate": "€30-50 (train + entry) OR private Uber (~€300 round trip)",
                    "price_level": PriceLevel.MODERATE,
                    "duration": "Full day (8am-6pm)",
                    "location": "Schwangau (near Füssen)",
                    "address": "Bayern ticket from Munich Hbf to Füssen, then bus to castle",
                    "distance_from_hotel": "2 hours by regional train OR 1h45 by private Uber",
                    "url": "https://www.neuschwanstein.de/englisch/tourist/index.htm",
                    "booking_required": True,
                    "best_time": "Morning train (7-8am) to beat crowds",
                    "confidence_score": 0.75,
                    "reasoning": "Only if you have a full free day and want the 'Germany experience'. With Uber Business, a private car makes it much easier but expensive (€300). Train is cheaper but requires transfers.",
                },
                {
                    "title": "Hofbräuhaus evening",
                    "category": ActivityCategory.FOOD,
                    "description": "Famous beer hall — litre steins, oompah band, tourist spectacle. Go once, embrace the chaos.",
                    "price_estimate": "€20-35/person",
                    "price_level": PriceLevel.MODERATE,
                    "duration": "1.5-2 hours",
                    "location": "Platzl 9 (near Marienplatz)",
                    "address": "Platzl 9, 80331 München",
                    "distance_from_hotel": "7 min walk from Courtyard Marriott",
                    "url": "https://www.hofbraeuhaus.de/en/",
                    "booking_required": False,
                    "best_time": "Evening (7-9pm) — live music, full energy",
                    "confidence_score": 0.7,
                    "reasoning": "Very touristy, but it's the archetypal Munich experience. Go if you've never been. Skip if you want 'authentic local'. Walking distance from your hotel.",
                },
            ],
        },
        # Add other cities as needed
    }

    def __init__(self):
        pass

    def generate_plan(
        self,
        location: str,
        date: Optional[str] = None,
        trip: Optional[Trip] = None,
        time_available: str = "All day",
    ) -> FreeDayPlan:
        """
        Generate a free-day plan for the given location.
        
        Args:
            location: City name (e.g., "Munich", "London")
            date: ISO date string (defaults to today)
            trip: Optional Trip object for context (hotel, etc.)
            time_available: "All day", "Morning", "Afternoon 2pm onwards", etc.
        
        Returns:
            FreeDayPlan with shopping + activity recommendations
        """
        if date is None:
            date = datetime.utcnow().date().isoformat()

        # Build context
        context = FreeDayContext(
            location=location,
            trip_id=trip.id if trip else None,
            trip_title=trip.title if trip else None,
            hotel_name=trip.hotels[0].name if trip and trip.hotels else None,
            hotel_address=trip.hotels[0].address if trip and trip.hotels else None,
            date=date,
            time_available=time_available,
            weather=self._get_weather(location),  # stubbed for now
        )

        # Get curated recommendations for this city
        city_data = self.CITY_DATA.get(location, {})
        
        shopping_recs = [
            ShoppingRecommendation(**rec) for rec in city_data.get("shopping", [])
        ]
        
        activity_recs = [
            ActivityRecommendation(**rec) for rec in city_data.get("activity", [])
        ]

        # Filter by time available
        if time_available != "All day":
            activity_recs = self._filter_by_time(activity_recs, time_available)

        # Sort by confidence + price level
        shopping_recs = sorted(shopping_recs, key=lambda x: (-x.confidence_score, x.price_level.value))
        activity_recs = sorted(activity_recs, key=lambda x: (-x.confidence_score, x.price_level.value))

        # Limit to top recommendations
        shopping_recs = shopping_recs[:6]
        activity_recs = activity_recs[:8]

        return FreeDayPlan(
            context=context,
            shopping_recommendations=shopping_recs,
            activity_recommendations=activity_recs,
        )

    def _get_weather(self, location: str) -> Optional[str]:
        """
        Get current weather for location.
        Stubbed for now — integrate OpenWeather API or similar.
        """
        # TODO: Integrate weather API
        return None

    def _filter_by_time(
        self, activities: list[ActivityRecommendation], time_available: str
    ) -> list[ActivityRecommendation]:
        """
        Filter activities by available time window.
        """
        time_lower = time_available.lower()
        
        # If only half-day, exclude full-day trips
        if "morning" in time_lower or "afternoon" in time_lower:
            activities = [a for a in activities if "full day" not in a.duration.lower()]
        
        return activities
