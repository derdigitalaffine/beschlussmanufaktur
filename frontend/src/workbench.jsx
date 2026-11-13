/* Read-only Mantine workbench on every authenticated Django page.
 * Domain decisions, HTML forms, CSRF, live/offline state and role checks
 * remain exclusively in their existing server-rendered applications.
 */
import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  ActionIcon, Anchor, Badge, Breadcrumbs, Button, Divider, Drawer,
  Group, MantineProvider, Modal, NavLink, Paper, Stack, Text, TextInput, ThemeIcon, Title,
} from '@mantine/core';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faArrowLeft, faArrowRight, faArrowUpRightFromSquare, faBars,
  faBookOpen, faCalendarDays, faCheckDouble, faChevronRight,
  faCircleInfo, faClipboardCheck, faFileCircleCheck, faFileLines,
  faFolderOpen, faGavel, faGear, faHouse, faIdBadge, faLayerGroup,
  faListCheck, faLock, faMagnifyingGlass, faPenToSquare, faShieldHalved,
  faSitemap, faTableList, faUsers, faWandMagicSparkles,
} from '@fortawesome/free-solid-svg-icons';
import './workbench.css';

const icon = (fa) => <FontAwesomeIcon icon={fa} aria-hidden="true" />;
const normalize = (value) => (value || '').replace(/\s+/g, ' ').trim();
const label = (element) => normalize(element?.textContent);
const routeGroup = [
  [/^(home|dashboard)$/, 'Arbeitsplatz', 'Ihr Einstieg in die fachliche Arbeit', faHouse],
  [/(templates|template_|kind_)/, 'Vorlagen', 'Entwürfe, Prüfschritte und freigegebene Fassungen', faFileLines],
  [/(meeting|invitation|session_returns)/, 'Sitzungen', 'Termine, Tagesordnung und Einladungen', faCalendarDays],
  [/(live_workspace|live_|votes|vote_)/, 'Sitzungsführung', 'Verbindliche Aktionen und dokumentierte Sitzungszustände', faClipboardCheck],
  [/(decision)/, 'Beschlusskontrolle', 'Beschlüsse, Fristen und Sachstandsverläufe', faGavel],
  [/(minute)/, 'Niederschrift', 'Fassungen, Prüfung und Veröffentlichung', faBookOpen],
  [/(member_desk|personal_note)/, 'Mein Arbeitsbereich', 'Persönliche Aufgaben und zugängliche Unterlagen', faIdBadge],
  [/(registry|kind_list|organization|person_profile|sample_data|imports)/, 'Stammdaten', 'Organisation, Gremien und gültige Zuordnungen', faSitemap],
  [/(users|membership|admin_form|grants)/, 'Menschen & Rollen', 'Einladungen und kontrollierte Berechtigungen', faUsers],
  [/(security|passkeys|recovery)/, 'Anmeldesicherheit', 'Zugriff und Wiederherstellungswege verwalten', faShieldHalved],
  [/(exchange|remote_review|replica|external_records)/, 'Bereitstellung', 'Freigaben und sichere Datenübergaben', faFolderOpen],
  [/(mail_inbox|emergency|tls_management)/, 'Betrieb', 'Zustellung, Sicherheit und Betriebszustände', faGear],
];
const category = (route) =>
  routeGroup.find(([pattern]) => pattern.test(route))?.slice(1)
  || ['Fachverwaltung', 'Berechtigter Arbeitskontext', faLayerGroup];

function authorizedUrl(anchor) {
  if (!anchor || !anchor.hasAttribute('href')) return null;
  const href = anchor.getAttribute('href');
  if (!href || href === '#' || href.startsWith('javascript:')) return null;
  try {
    const url = new URL(href, window.location.href);
    if (url.origin !== window.location.origin || !['http:', 'https:'].includes(url.protocol)) return null;
    return url.pathname + url.search + url.hash;
  } catch { return null; }
}

function allowedLinks() {
  return [...document.querySelectorAll('.global-nav a[href]')]
    .map((node) => ({ text: label(node), href: authorizedUrl(node), active: node.hasAttribute('aria-current') }))
    .filter(({ text, href }) => Boolean(text && href));
}

function pageSections() {
  const excluded = 'form, li, .ui-item, [id$="-fallback"], [hidden], .page-heading, .ui-hero, .bm-workbench-root';
  const headings = [...document.querySelectorAll('#inhalt h2, #inhalt h3')];
  const used = new Set();
  return headings.filter((node) => {
    if (node.closest(excluded)) return false;
    if (node.tagName === 'H3' && !node.closest('section')) return false;
    if (node.tagName === 'H3' && headings.some((h) => h !== node && h.tagName === 'H2' && h.parentElement === node.parentElement)) return false;
    const name = label(node);
    if (!name || name.length > 75 || used.has(name)) return false;
    used.add(name);
    return true;
  }).slice(0, 9).map((node, index) => {
    if (!node.id) {
      const id = `bm-section-${index + 1}`;
      if (!document.getElementById(id)) node.id = id;
    }
    return { title: label(node), id: node.id };
  }).filter(({ id }) => Boolean(id));
}

function pageActions() {
  const selector = '.ui-hero-actions a[href], .page-heading a.primary[href], .page-heading > a[href], .ui-header .ui-button[href]';
  const seen = new Set();
  return [...document.querySelectorAll(selector)].map((node) => ({
    text: label(node), href: authorizedUrl(node),
    primary: node.classList.contains('primary') || node.classList.contains('ui-button--primary'),
  })).filter((action) => {
    if (!action.href || !action.text || action.text.length > 52 || seen.has(action.href)) return false;
    seen.add(action.href);
    return true;
  }).slice(0, 2);
}

function Workbench({ route, sections, links, actions }) {
  const [drawer, setDrawer] = useState(false);
  const [quickOpen, setQuickOpen] = useState(false);
  const [quickQuery, setQuickQuery] = useState('');
  const [title, description, fa] = category(route);
  const matches = links.filter((link) =>
    link.text.toLocaleLowerCase('de-DE').includes(quickQuery.trim().toLocaleLowerCase('de-DE'))
  );
  // No extra routes or permission rules: the model only contains server-rendered links.
  useEffect(() => {
    const openByKeyboard = (event) => {
      if ((event.ctrlKey || event.metaKey) && !event.altKey && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setDrawer(false);
        setQuickQuery('');
        setQuickOpen(true);
      }
    };
    document.addEventListener('keydown', openByKeyboard);
    return () => document.removeEventListener('keydown', openByKeyboard);
  }, []);

  return (
    <div className="bm-workbench" data-testid="bm-workbench">
      <Paper withBorder radius="xl" className="bm-workbench-banner">
        <Group className="bm-workbench-banner-row" justify="space-between" align="center" wrap="wrap" gap="md">
          <Group gap="md" align="center" wrap="nowrap">
            <ThemeIcon className="bm-workbench-emblem" size={46} variant="light" radius="lg">
              {icon(fa)}
            </ThemeIcon>
            <Stack gap={3} className="bm-workbench-context">
              <Breadcrumbs separator={icon(faChevronRight)} className="bm-workbench-breadcrumbs" aria-label="Seitenpfad">
                <Anchor href="/" underline="never">Arbeitsplatz</Anchor>
                <Text span>{title}</Text>
              </Breadcrumbs>
              <Text size="sm" className="bm-workbench-description">{description}</Text>
            </Stack>
          </Group>
          <Group gap="xs" className="bm-workbench-actions" wrap="wrap">
            {actions.map((action) => (
              <Button key={action.href} component="a" href={action.href}
                variant={action.primary ? 'filled' : 'light'} color="teal"
                size="sm" radius="md"
                rightSection={icon(faArrowUpRightFromSquare)}
              >
                {action.text}
              </Button>
            ))}
            {links.length > 0 && <Button variant="light" className="bm-workbench-quick"
              aria-keyshortcuts="Control+K Meta+K" title="Tastenkürzel: Strg + K oder ⌘ + K"
              leftSection={icon(faMagnifyingGlass)} onClick={() => { setDrawer(false); setQuickQuery(''); setQuickOpen(true); }}
              radius="md">Schnellwechsel <span className="bm-shortcut-label">Strg/⌘ K</span></Button>}
            {links.length > 0 && <Button variant="default" className="bm-workbench-open"
              leftSection={icon(faBars)} onClick={() => setDrawer(true)} radius="md"
              aria-label="Alle für mich verfügbaren Bereiche öffnen">
              Bereiche
            </Button>}
          </Group>
        </Group>
      </Paper>
      {sections.length >= 2 && (
        <nav className="bm-workbench-index" aria-label="Abschnitte dieser Seite">
          <Group gap="xs" wrap="nowrap">
            <Badge variant="light" color="gray" size="md" className="bm-index-label">
              {icon(faListCheck)} <span>Auf dieser Seite</span>
            </Badge>
            <div className="bm-workbench-index-scroll">
              {sections.map((section) => (
                <Anchor key={section.id} href={`#${section.id}`}
                  className="bm-index-link" underline="never">
                  {section.title}
                </Anchor>
              ))}
            </div>
          </Group>
        </nav>
      )}
      <Modal opened={quickOpen} onClose={() => setQuickOpen(false)}
         title="Bereich schnell wechseln" centered size="md" className="bm-quick-modal"
         aria-label="Schnellnavigation zu freigegebenen Arbeitsbereichen">
         <Text size="sm" c="dimmed" mb="sm">
           Suchen Sie einen Bereich. Mit Enter öffnen Sie den ersten Treffer; Esc schließt die Auswahl.
         </Text>
         <TextInput label="Bereich finden" placeholder="Zum Beispiel: Sitzungen"
           value={quickQuery} onChange={(event) => setQuickQuery(event.currentTarget.value)}
           maxLength={60} autoFocus
           leftSection={icon(faMagnifyingGlass)}
           onKeyDown={(event) => {
             if (event.key === 'Enter' && matches.length) {
               event.preventDefault();
               window.location.assign(matches[0].href);
             }
           }} />
         <nav aria-label="Schnellnavigation" className="bm-quick-results">
           {matches.length ? matches.map((link) => (
             <NavLink key={link.href} label={link.text} href={link.href}
               active={link.active} leftSection={icon(faArrowRight)}
               className="bm-workbench-navlink" />
           )) : <Text c="dimmed" size="sm" py="md">
             Kein passender Bereich. Für Sitzungen und Vorlagen können Sie die globale Suche verwenden.
           </Text>}
         </nav>
       </Modal>
       <Drawer opened={drawer} onClose={() => setDrawer(false)} title="Bereiche und Aufgaben"
        position="right" size="sm" className="bm-area-drawer"
        aria-label="Für diesen Arbeitskontext freigegebene Navigation">
        <Text size="sm" c="dimmed" mb="md">
          Hier erscheinen nur die Arbeitsbereiche, die das Fachsystem im aktuellen Kontext anbietet.
        </Text>
        <Stack gap={4}>
          {links.map((link) => (
            <NavLink key={link.href} label={link.text} href={link.href}
              leftSection={icon(faArrowRight)} className="bm-workbench-navlink"
              active={link.active}
            />
          ))}
        </Stack>
        <Divider my="lg" />
        <Button component="a" href="/" variant="light" color="teal" fullWidth
          leftSection={icon(faHouse)}>Zum Arbeitsplatz</Button>
      </Drawer>
    </div>
  );
}

class Boundary extends React.Component {
  constructor(props) { super(props); this.state = { failed: false }; }
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch() { /* Django content and navigation were never replaced. */ }
  render() { return this.state.failed ? null : this.props.children; }
}

function initialize() {
  const root = document.getElementById('bm-workbench-root');
  if (!root || !document.body.classList.contains('bm-private-ui')) return;
  const route = document.body.dataset.bmRoute || '';
  const model = {
    route, sections: pageSections(), actions: pageActions(), links: allowedLinks(),
  };
  createRoot(root).render(
    <Boundary>
      <MantineProvider withCSSVariables={false} defaultColorScheme="light">
        <Workbench {...model} />
      </MantineProvider>
    </Boundary>
  );
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initialize, { once: true });
} else {
  initialize();
}
