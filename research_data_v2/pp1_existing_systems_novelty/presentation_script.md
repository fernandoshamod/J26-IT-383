# Two-minute English presentation script

Approx. 255 words, about two minutes at a measured speaking pace. References and qualification are in [the slide draft](./pp1_slides.md).

“Existing platforms such as The Knot, WeddingWire, Zola and Eventective already help users discover vendors, compare reviews and prices, and contact businesses. Zola and The Knot also describe personalized recommendations. So my novelty claim is **not** that vendor recommendations are new.

Research on supplier selection covers multiple criteria and multiple suppliers. Package recommender research studies groups of items, while explainable AI and scheduling research provide methods for understanding decisions and operational constraints. My research question is how to bring these ideas together for an event request in a way that users can inspect, especially when important evidence is missing.

PlanoVision currently accepts an event’s services, location, guest count and budget. It filters recorded service options, searches bounded combinations with distinct vendors, and ranks the examined packages using cost efficiency, review-derived risk favorability and service-category compatibility. It also explains each result and diagnoses why a request has no matching package. A separate research page demonstrates synthetic vendor-pair conflict checks; this is not yet part of live package ranking.

The saved Random Forest is called in the recommendation pipeline, but its target labels come from review-based rules. Therefore, its reported accuracy measures agreement with those rules, not real-world vendor reliability. Package prices and service areas are synthetic. Availability, collaboration and booking feasibility still require verification. Even when packages are returned, the search may reach a candidate limit, so I describe them as the best among examined combinations.

For the next research stage, I would compare against cost-only and simpler search baselines, test search quality on tractable exhaustive subsets, obtain independent operational labels and Sri Lankan vendor data, and evaluate whether the explanations actually help users. At PP1, I can demonstrate the implemented workflow and state these validation limits clearly.”
