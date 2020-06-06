Election ImageMap Generator
===========================

This is a project to generate from metadata the clickable image maps for every U.S. Presidential Election
on Wikipedia. It was created because some maps didn't exist, and the existing maps had inconsistencies -
there were two copies of Massachussets in many maps, Oregon was clickable long before it was a state,
callout labels were not always clickable, and so on.

This script pulls the required wiki files down, alters them to match its understanding of history,
and re-uploads any pages that need changing. It is a semi-automated scriptp that is run manually,
but does the actual editing and uploading by itself.

It is now capable of generating a complete set of imagemaps from 1789 to 2020, as of this writing.
The basic corrections are in place, but there are a few small issues left to be resolved. Those are listed below.

TODO:
 - The Platt Purchase is depicted as being part of Missouri long before it was actually integrated into the state
 - Clickable areas are way more detailed than necessary, should use simplified outlines

Future ideas:
 - Generate imagemaps for House of Representatives elections
 - Generate underlying SVGs in addition to imagemaps
