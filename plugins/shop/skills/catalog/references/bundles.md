# Bundles

A bundle is several file items sold together at one price. The catalog skill's rules (only the changes the
user asked for, confirmations, approvals, untrusted text) apply here too.

- `create_bundle(category_id, title, price_stars)` (a price of 1 to 100,000 Stars) creates a bundle that
  stays hidden until it holds at least two items and is published. Then
  `update_bundle(bundle_id, add_item_id, remove_item_id)` with exactly one of `add_item_id` and
  `remove_item_id` per call; orders already placed keep the items they had. The result is the bundle as an
  item, with `warning` set when it holds fewer than 2 items (it still sells if on sale) and
  `publish_blocker` saying why it cannot be published.
- Adding an item to a bundle sets a price (the item then sells for a share of the bundle's), so it needs
  `pricing:write`. An add that leaves the bundle priced under half of what its items sell for apart needs the
  owner's approval: the answer is `pending_approval`, and the item is not in the bundle until the owner
  approves. Never change the bundle's price or its other items on your own to avoid the approval.
