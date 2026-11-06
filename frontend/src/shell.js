/* Licensed Font Awesome 7 icons are bundled locally, not loaded from a CDN.
   Never render user-supplied icon markup; only definitions in this allowlist. */
import { config, icon } from '@fortawesome/fontawesome-svg-core';
import {
  faHouse,
  faFileLines,
  faCalendarDays,
  faGavel,
  faUserTie,
  faBuilding,
  faUsers,
  faShieldHalved,
  faRightFromBracket,
  faMagnifyingGlass,
  faArrowLeft,
  faUserPlus,
  faChevronRight,
  faCircleCheck,
  faCircleInfo,
  faClock,
  faArrowRight,
} from '@fortawesome/free-solid-svg-icons';

config.autoAddCss = false;
const icons = {
  home: faHouse,
  documents: faFileLines,
  meetings: faCalendarDays,
  decisions: faGavel,
  desk: faUserTie,
  organization: faBuilding,
  users: faUsers,
  security: faShieldHalved,
  logout: faRightFromBracket,
  search: faMagnifyingGlass,
  back: faArrowLeft,
  invite: faUserPlus,
  next: faChevronRight,
  success: faCircleCheck,
  info: faCircleInfo,
  clock: faClock,
  arrow: faArrowRight,
};

for (const element of document.querySelectorAll('[data-fa-icon]')) {
  const definition = icons[element.getAttribute('data-fa-icon')];
  if (!definition) continue;
  const svg = icon(definition, { attributes: { 'aria-hidden': 'true', focusable: 'false' } });
  if (!svg) continue;
  // The SVG comes only from the static Font Awesome allowlist, not from HTML input.
  element.innerHTML = svg.html.join('');
}
