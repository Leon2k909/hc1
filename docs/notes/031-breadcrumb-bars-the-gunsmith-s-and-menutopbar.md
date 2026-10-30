## Breadcrumb bars (the gunsmith's and `MenuTopbar`)
- Every breadcrumb bar looks like the gunsmith's, which the user asked for: a bordered back button, then the trail with
  the current page in orange. The gunsmith's `.gs-crumbs` and the menu pages' `MenuTopbar` both draw it with the
  mixins in `Code/UI/Styles/Breadcrumbs.scss`, so change the look there. Pages only set the bar's side padding (48 px,
  24 px in portrait) to line it up with their content; don't give them their own height or font sizes again.
- A page inside another passes `ParentTitle` / `ParentAction` (Profile › Career Record, Profile › a section). Don't
  name a Panel property `Parent`: it hides `Panel.Parent`, and it compiled without complaint.

