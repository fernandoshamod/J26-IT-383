# OpenStreetMap Sri Lanka pilot collection

Collected on **2026-10-19T06:26:41Z**. This is a small sample of **10 named OSM mapped business listings** (7 Photography, 3 Catering), not independently confirmed current vendors, event packages or booking availability. The sample is stored in [osm_sri_lanka_vendor_sample.csv](./osm_sri_lanka_vendor_sample.csv). The original [header-only template](./sri_lanka_vendor_profiles.csv) was not overwritten.

## Source and method

- Source: [Geofabrik Sri Lanka OpenStreetMap PBF extract](https://download.geofabrik.de/asia/sri-lanka.html), direct file https://download.geofabrik.de/asia/sri-lanka-latest.osm.pbf. Download returned **HTTP 200**, Content-Length **144,470,045 bytes**, Last-Modified **Sun, 18 Oct 2026 22:43:38 GMT**. Downloaded file SHA-256: **3611d4421727b3ea7971a49a01ca32432001453fa2c9a5cd40068162bcfb9f28**.
- The extract was streamed with pyosmium. Across named nodes, ways and relations, the scan found **32 objects tagged craft=photographer** and **9 tagged craft=caterer**. These are tag counts, not verified active businesses. The 10 selected objects are distinct OSM nodes with a name and addr:city tag. Their tags and IDs were rechecked in a second pass before the CSV was written.
- Country is inferred from the country extract, while each CSV city is copied **exactly** from that object's addr:city tag. District and province were not present on selected objects and remain blank. No geocoding, price estimation or review-score imputation was performed.
- A bounded five-branch Overpass request for photographer, caterer, party shop, event rental and music venue proxies in a Colombo bounding box returned **HTTP 406 Not Acceptable** from the main Overpass API on 2026-10-19 around 06:27 UTC. A Python HEAD request to that API timed out. A different Overpass endpoint responded but returned zero even for common Colombo restaurant nodes; it was not used as absence evidence. An earlier alternate endpoint returned HTTP 500. The permitted Geofabrik extract was used instead; no restriction was bypassed.
- Category mapping used only explicit craft=photographer and craft=caterer tags, consistent with the [OSM photographer tag](https://wiki.openstreetmap.org/wiki/Tag%3Acraft%3Dphotographer) and [OSM caterer tag](https://wiki.openstreetmap.org/wiki/Tag%3Acraft%3Dcaterer). A photographer workplace tag does not confirm wedding service, and a caterer workplace tag does not confirm a quote or event date.
- [shop=party](https://wiki.openstreetmap.org/wiki/Tag%3Ashop%3Dparty) means a party-supply shop, [rental=event](https://wiki.openstreetmap.org/wiki/Tag%3Arental%3Devent) can include many equipment types, and a music venue is not an entertainer. These proxies were **not** converted into Decoration, Audio Visual or Entertainment vendor records. Category coverage is therefore 0 in those three categories; this is not a claim that Sri Lanka has no such vendors.

## Selected OSM evidence

| OSM element ID | Name as mapped | Category | Category tag | addr:city as mapped |
|---|---|---|---|---|
| [node/4052191589](https://www.openstreetmap.org/node/4052191589) | Champs Photographers | Photography | craft=photographer | Bambalapitiya |
| [node/4322760583](https://www.openstreetmap.org/node/4322760583) | Chandana Photo | Photography | craft=photographer | Welimada |
| [node/4579787826](https://www.openstreetmap.org/node/4579787826) | Praveen Creations | Photography | craft=photographer | Boyagane |
| [node/5139403360](https://www.openstreetmap.org/node/5139403360) | Emerald Studio | Photography | craft=photographer | Malabe |
| [node/5168435672](https://www.openstreetmap.org/node/5168435672) | Jasmine Pics Studio | Photography | craft=photographer | Galle |
| [node/6615745068](https://www.openstreetmap.org/node/6615745068) | Ray Mac Photos | Photography | craft=photographer | Boralesgamuwa |
| [node/6631008162](https://www.openstreetmap.org/node/6631008162) | Editing Table Studio | Photography | craft=photographer | Nugegoda |
| [node/2724797189](https://www.openstreetmap.org/node/2724797189) | Dushan Caterers | Catering | craft=caterer | Habarakada |
| [node/6615719999](https://www.openstreetmap.org/node/6615719999) | East West Foods Pvt Ltd | Catering | craft=caterer | Colombo |
| [node/6615744992](https://www.openstreetmap.org/node/6615744992) | The High Tea Catering Service | Catering | craft=caterer | Maharagama |

The names, cities, OSM element IDs and craft tags above are measured from the downloaded extract. Whether any mapped place still operates, offers the desired event service, travels to an event location, or is available on a date is **unverified**. Avoid presenting these as confirmed bookable vendors.

