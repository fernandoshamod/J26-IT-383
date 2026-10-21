# Selected vendor category check

Source: [real_vendor_profiles.csv](../../hybrid_simulation_v1/real_vendor_profiles.csv), filtered by the four IDs in the live API response. These source tags support category-level inference. Service options, LKR prices, service areas, availability and booking are synthetic or unverified, **not verified real vendor offerings**.

| Vendor and ID | Demo service | Original category evidence | Assessment |
|---|---|---|---|
| Minibooths `FQ_QUyrwtnaEdxUxruZkXg` | Photography | `Photo Booth Rentals`, `Event Photography`, `Photographers`; matched `Event Photography; Photographers` | Category support: PASS. Exact package and booking: NOT_VERIFIED. |
| Petit Jardin En Ville `_t_UwNkwAinJSljDDYvnoQ` | Decoration | `Florists`, `Wedding Planning`; matched `Florists; Wedding Planning` | Category support: PASS. Exact service and booking: NOT_VERIFIED. |
| Carl Alan Floral Designs LTD `P7MHW-EtCdp3eVF2P_nX0A` | Decoration | `Floral Designers`, `Florists`, `Party Supplies`; matched `Floral Designers; Florists` | Category support: PASS. Exact service and booking: NOT_VERIFIED. |
| Riehs Florist `zwl7iLwHBTdkb5-0gNgGFg` | Decoration | `Florists`, `Floral Designers`; matched `Floral Designers; Florists` | Category support: PASS. Exact service and booking: NOT_VERIFIED. |

The profile `service_categories` values are derived labels. [Category audit](../pp1_final_technical_audit/vendor_category_issues.md) documents that the original classification script is unavailable and the option rows are synthetic. Present each as a source-category match with a **simulated** event option.
