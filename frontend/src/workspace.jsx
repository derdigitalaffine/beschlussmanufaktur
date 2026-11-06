/* Mantine progressive islands. Browser never gets domain authority: all postbacks
   retain original Django actions, CSRF, hidden version values and validation. */
import React, { useEffect } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Alert, Anchor, Badge, Button, Checkbox, Divider,
  Group, MantineProvider, NativeSelect, Paper, Stack,
  Text, Textarea, TextInput, ThemeIcon, Timeline, Title,
} from '@mantine/core';
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import {
  faArrowLeft, faArrowRight, faCalendarDays, faCheck, faChevronRight,
  faCircleExclamation, faCircleInfo, faClipboardCheck, faClock,
  faFileLines, faGavel, faLock, faShieldHalved, faStar, faUserPlus,
  faUsers,
} from '@fortawesome/free-solid-svg-icons';
import '@mantine/core/styles.layer.css';
import './workspace.css';

const glyph = (definition) => <FontAwesomeIcon icon={definition} aria-hidden="true" />;
const clean = (node) => node?.textContent?.trim() || '';
const target = (el) => el?.getAttribute('href') || '#';
const displayLabel = (node) => clean(node).replace(/\s+/g, ' ').trim();

function Ready({ children, fallback, hiddenCompanions = [] }) {
  useEffect(() => {
    // Keep the authorized Django content until the entire enhanced view mounts.
    const nodes = [fallback, ...hiddenCompanions].filter(Boolean);
    for (const node of nodes) node.hidden = true;
    return () => { for (const node of nodes) node.hidden = false; };
  }, [fallback]);
  return children;
}

class IslandBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch() {
    // Keep all native content available if the client island ever fails.
    for (const node of [this.props.fallback, ...(this.props.hiddenCompanions || [])]) {
      if (node) node.hidden = false;
    }
  }
  render() {
    return this.state.failed ? null : this.props.children;
  }
}

function mount(element, fallback, child, hiddenCompanions = []) {
  if (!element || !fallback) return;
  createRoot(element).render(
    <IslandBoundary fallback={fallback} hiddenCompanions={hiddenCompanions}>
      <MantineProvider withCSSVariables={false} defaultColorScheme="light">
        <Ready fallback={fallback} hiddenCompanions={hiddenCompanions}>{child}</Ready>
      </MantineProvider>
    </IslandBoundary>
  );
}

function WorkflowCard({ icon, label, title, detail, action, url, secondary, secondaryUrl }) {
  return (
    <Paper className="bm-feature" radius="xl" withBorder>
      <Group justify="space-between" align="flex-start" mb="lg">
        <ThemeIcon className="bm-feature-icon" size={48} radius="lg" variant="light">
          {glyph(icon)}
        </ThemeIcon>
        <Badge className="bm-feature-badge" variant="light" color="teal" radius="sm">
          {label}
        </Badge>
      </Group>
      <Title order={2} className="bm-feature-title">{title}</Title>
      <Text className="bm-feature-desc" mt="sm">{detail}</Text>
      <Group className="bm-feature-actions" mt="xl" gap="md">
        {action && <Button component="a" href={url} size="md" radius="md" rightSection={glyph(faArrowRight)}>
          {action}
        </Button>}
        {secondary && <Anchor href={secondaryUrl} className="bm-secondary-link">{secondary}</Anchor>}
      </Group>
    </Paper>
  );
}

function Dashboard({ fallback }) {
  const heading = displayLabel(fallback.querySelector('h2'));
  const description = displayLabel(fallback.querySelector('h2 + p'));
  const mainAction = fallback.querySelector('.next-step-action .primary');
  const secondaryAction = fallback.querySelector('.next-step-action a:not(.primary)');
  const meeting = document.querySelector('.today-work-panel:first-child');
  const decision = document.querySelector('.today-work-panel:nth-child(2)');
  const meetingLink = meeting?.querySelector('h4 a, .today-work-action');
  const decisionCount = decision?.querySelector('.today-task-count');
  const tasks = Array.from(decision?.querySelectorAll('.today-task-list li') || []).map((node) => {
    const link = node.querySelector('a[href]');
    return {
      title: clean(link),
      url: target(link),
      detail: clean(node.querySelector('p')),
      overdue: Boolean(node.querySelector('.today-overdue')),
    };
  }).filter((task) => task.title);
  const role = document.querySelector('#arbeitskontext .pill');
  const context = document.querySelector('#context-title');

  return (
    <div className="bm-mantine-dashboard" data-testid="bm-mantine-dashboard">
      <div className="bm-section-label">{glyph(faStar)} <span>Ihr digitaler Arbeitsplatz</span></div>
      <Group justify="space-between" align="flex-end" mb="md">
        <div>
          <Title order={2} className="bm-spotlight-heading">Was steht als Nächstes an?</Title>
          <Text className="bm-spotlight-subline">
            Konkrete Aufgaben statt technischer Menüs – alle Aktionen bleiben an Ihren Arbeitskontext gebunden.
          </Text>
        </div>
        {role && <Badge variant="light" color="teal" radius="sm" className="bm-role-badge">
          {displayLabel(context)} · {displayLabel(role)}
        </Badge>}
      </Group>
      <div className="bm-dashboard-grid">
        <div className="bm-dashboard-primary">
          <WorkflowCard
            icon={faClipboardCheck}
            label="Empfohlener Einstieg"
            title={heading}
            detail={description}
            action={clean(mainAction)}
            url={target(mainAction)}
            secondary={clean(secondaryAction)}
            secondaryUrl={target(secondaryAction)}
          />
        </div>
        <div className="bm-dashboard-secondary">
          <Stack gap="md" className="bm-side-stack">
            <Paper withBorder radius="lg" className="bm-overview-card">
              <Group align="flex-start" gap="md" wrap="nowrap">
                <ThemeIcon variant="light" size="xl" color="blue" radius="lg">{glyph(faCalendarDays)}</ThemeIcon>
                <div>
                  <Text className="bm-overview-label">Nächste Sitzung</Text>
                  <Title order={3} className="bm-overview-title">
                    {meetingLink ? displayLabel(meetingLink) : 'Noch kein Termin'}
                  </Title>
                  <Anchor href={target(meetingLink)} className="bm-overview-action">
                    Zum Sitzungskalender {glyph(faChevronRight)}
                  </Anchor>
                </div>
              </Group>
            </Paper>
            {decision && <Paper withBorder radius="lg" className="bm-overview-card">
              <Group align="center" gap="md" wrap="nowrap">
                <ThemeIcon variant="light" size="xl" color="orange" radius="lg">{glyph(faGavel)}</ThemeIcon>
                <div>
                  <Text className="bm-overview-label">Offene Beschlussaufgaben</Text>
                  <Title order={3} className="bm-overview-count">{clean(decisionCount) || '0'}</Title>
                  <Anchor href={target(decision.querySelector('a.today-work-action'))} className="bm-overview-action">
                    Sachstände prüfen {glyph(faChevronRight)}
                  </Anchor>
                </div>
              </Group>
            </Paper>}
          </Stack>
        </div>
      </div>
      {tasks.length > 0 && (
        <Paper className="bm-task-worklist" withBorder radius="xl" mt="lg">
          <Group justify="space-between" align="center" gap="md" mb="md">
            <Group gap="sm">
              <ThemeIcon variant="light" size={36} color="orange" radius="md">{glyph(faClipboardCheck)}</ThemeIcon>
              <Title order={3}>Meine nächsten Beschlussaufgaben</Title>
            </Group>
            <Anchor href={target(decision?.querySelector('a.today-work-action'))}>Alle Aufgaben ansehen</Anchor>
          </Group>
          <Stack gap={0}>
            {tasks.map((task, index) => (
              <Group key={task.url + '-' + index} className="bm-task-row" justify="space-between" align="center" wrap="nowrap" gap="sm">
                <div>
                  <Anchor href={task.url} className="bm-task-title">{task.title}</Anchor>
                  <Text size="sm" className="bm-task-detail">{task.detail}</Text>
                </div>
                <Badge variant="light" color={task.overdue ? 'red' : 'gray'} radius="sm">
                  {task.overdue ? 'Überfällig' : 'Offen'}
                </Badge>
              </Group>
            ))}
          </Stack>
        </Paper>
      )}
    </div>
  );
}

function modelForm(form) {
  const inputs = Array.from(form.querySelectorAll('input[name],select[name],textarea[name]'));
  const fields = inputs.map((el) => {
    const tag = el.tagName.toLowerCase();
    const label = Array.from(form.querySelectorAll('label')).find((item) => item.control === el);
    const container = el.closest('.field, .users-field');
    return {
      name: el.name,
      type: tag === 'select' ? 'select' : tag === 'textarea' ? 'textarea' : (el.getAttribute('type') || 'text'),
      id: el.id || undefined,
      label: displayLabel(label).replace(/\s+\*$/, ''),
      value: el.value,
      required: el.required,
      maxLength: el.maxLength >= 0 ? el.maxLength : undefined,
      options: tag === 'select'
        ? Array.from(el.options).map((option) => ({ value: option.value, label: option.label }))
        : [],
      error: displayLabel(container?.querySelector('.errorlist, .users-field-error')),
      help: displayLabel(container?.querySelector('.ui-small, .help')),
      autocomplete: el.getAttribute('autocomplete') || undefined,
    };
  });
  return {
    action: form.action,
    method: form.method,
    fields,
    nonFieldErrors: displayLabel(form.querySelector('.errorlist.nonfield')),
  };
}

function FormField({ field }) {
  const props = {
    label: field.label,
    name: field.name,
    id: field.id,
    defaultValue: field.value,
    required: field.required,
    error: field.error || undefined,
    description: field.help || undefined,
    className: 'bm-control',
  };

  if (field.type === 'hidden') {
    return <input type="hidden" name={field.name} defaultValue={field.value} key={field.name} />;
  }
  if (field.type === 'select') {
    return <NativeSelect key={field.name} {...props} data={field.options} />;
  }
  if (field.type === 'textarea') {
    return <Textarea key={field.name} {...props} minRows={4} autosize maxLength={field.maxLength} />;
  }
  return <TextInput key={field.name} {...props} type={field.type} maxLength={field.maxLength} autoComplete={field.autocomplete} />;
}

function Fields({ form, danger = false, submitLabel, info, backUrl, backLabel, compact = false }) {
  const hidden = form.fields.filter((f) => f.type === 'hidden');
  const primaryFields = form.fields.filter((f) => f.type !== 'hidden' && f.name !== 'reason');
  const reasonField = form.fields.find((f) => f.name === 'reason');
  const requiresConfirmation = danger;
  return (
    <form action={form.action} method={form.method} className="bm-mantine-form">
      {hidden.map((field) => <FormField key={field.name} field={field} />)}
      {form.nonFieldErrors && <Alert color="red" icon={glyph(faCircleExclamation)} title="Bitte prüfen" role="alert">
        {form.nonFieldErrors}
      </Alert>}
      <Stack gap="md">
        {primaryFields.map((field) => <FormField key={field.name} field={field} />)}
        {reasonField && <Paper className="bm-form-reason" radius="lg" withBorder>
          <Group gap="sm" mb="sm">
            <ThemeIcon color={danger ? 'red' : 'teal'} variant="light" size="md" radius="md">
              {glyph(faFileLines)}
            </ThemeIcon>
            <Text fw={750}>Begründung dokumentieren</Text>
          </Group>
          <FormField field={reasonField} />
          <Text className="bm-form-helper" mt="sm">
            Die Begründung ist Teil des nachvollziehbaren Änderungsverlaufs.
          </Text>
        </Paper>}
        {info && <Alert variant="light" color={danger ? 'orange' : 'teal'} title="Gut zu wissen"
          icon={glyph(faCircleInfo)}>{info}</Alert>}
        {requiresConfirmation && <Checkbox
          label="Ich habe Rolle und Folgen dieser Änderung geprüft."
          required
          className="bm-confirm-check"
        />}
        <Group justify={compact ? 'stretch' : 'flex-end'} gap="sm" className="bm-form-actions">
          {backUrl && <Button component="a" href={backUrl} variant="default" leftSection={glyph(faArrowLeft)}>
            {backLabel || 'Abbrechen'}
          </Button>}
          <Button type="submit" color={danger ? 'red' : 'teal'} className="bm-submit"
            leftSection={glyph(danger ? faShieldHalved : faCheck)} fullWidth={compact}>
            {submitLabel}
          </Button>
        </Group>
      </Stack>
    </form>
  );
}

function Membership({ model, fallback }) {
  const title = clean(fallback.querySelector('.page-heading h1')) || 'Zugriff verwalten';
  const subtitle = clean(fallback.querySelector('.page-heading p'));
  const back = fallback.querySelector('a.text-link');
  const button = clean(fallback.querySelector('button[type="submit"]')) || 'Änderung speichern';
  const help = clean(fallback.querySelector('.help'));
  const danger = /entzieh|zurückzieh|widerruf/i.test(title + ' ' + button);
  return (
    <div className="bm-mantine-membership" data-testid="bm-mantine-membership">
      <Anchor href={target(back)} className="bm-mantine-back" underline="never">
        {glyph(faArrowLeft)} {clean(back) || 'Zurück zur Verwaltung'}
      </Anchor>
      <div className="bm-mantine-heading">
        <Badge color={danger ? 'red' : 'teal'} variant="light" radius="sm">
          {glyph(danger ? faShieldHalved : faUsers)} {danger ? 'Sicherheitsrelevante Aktion' : 'Berechtigungsverwaltung'}
        </Badge>
        <Title order={1}>{title}</Title>
        <Text>{subtitle}</Text>
      </div>
      <div className="bm-membership-grid">
        <div className="bm-membership-main">
          <Paper className="bm-mantine-mainform" radius="xl" withBorder>
            <Group justify="space-between" mb="xl" align="center">
              <div>
                <Text className="bm-overline">Schritt 1 von 1</Text>
                <Title order={2}>Änderung prüfen und bestätigen</Title>
              </div>
              <ThemeIcon variant="light" size={46} color={danger ? 'red' : 'teal'} radius="lg">
                {glyph(danger ? faLock : faClipboardCheck)}
              </ThemeIcon>
            </Group>
            <Fields form={model} danger={danger} submitLabel={button}
              info={help} backUrl={target(back)} />
          </Paper>
        </div>
        <div className="bm-membership-sidebar">
          <Paper className="bm-mantine-aside" radius="xl" withBorder>
            <Group gap="xs" mb="lg">
              <ThemeIcon size="lg" variant="light" color="teal">{glyph(faShieldHalved)}</ThemeIcon>
              <Title order={3}>So bleibt es sicher</Title>
            </Group>
            <Timeline bulletSize={28} lineWidth={2} active={1}>
              <Timeline.Item bullet={glyph(faUsers)} title="Arbeitskontext">
                <Text size="sm">Die Änderung gilt ausschließlich für diese Körperschaft.</Text>
              </Timeline.Item>
              <Timeline.Item bullet={glyph(faFileLines)} title="Dokumentation">
                <Text size="sm">Rolle, Zeiträume und Begründung werden durch den Server geprüft.</Text>
              </Timeline.Item>
              <Timeline.Item bullet={glyph(faCheck)} title="Bestätigung">
                <Text size="sm">Erst nach dem Absenden bestätigt der Server die Änderung.</Text>
              </Timeline.Item>
            </Timeline>
            <Divider my="lg" />
            <Text size="sm" className="bm-aside-caption">
              Ein sichtbarer Klick ist noch keine Berechtigungsänderung. Entscheidend ist die Serverantwort.
            </Text>
          </Paper>
        </div>
      </div>
    </div>
  );
}

function Invitation({ model }) {
  return (
    <div className="bm-mantine-invitation" data-testid="bm-mantine-invitation">
      <Paper className="bm-invite-highlight" radius="lg">
        <Group gap="sm" align="flex-start">
          <ThemeIcon size={42} radius="lg" variant="light" color="teal">{glyph(faUserPlus)}</ThemeIcon>
          <div>
            <Text fw={750}>Persönliche Einladung</Text>
            <Text size="sm">Berechtigung erst nach Annahme. Kein sofortiger Kontozugriff.</Text>
          </div>
        </Group>
      </Paper>
      <Fields form={model} submitLabel="Einladung senden" compact
        info="Gültigkeitsbeginn, Ende und fachliche Rolle werden auf dem Server validiert." />
    </div>
  );
}

// Progressive enhancement: native HTML remains functional without JavaScript.
const dashboardNode = document.getElementById('mantine-dashboard');
const dashboardFallback = document.querySelector('.next-step');
if (dashboardNode && dashboardFallback) mount(
  dashboardNode, dashboardFallback,
  <Dashboard fallback={dashboardFallback} />,
  [document.querySelector('.today-work')]
);

const membershipNode = document.getElementById('mantine-membership');
const membershipFallback = document.getElementById('membership-fallback');
const membershipForm = membershipFallback?.querySelector('form');
if (membershipNode && membershipForm) mount(
  membershipNode, membershipFallback,
  <Membership model={modelForm(membershipForm)} fallback={membershipFallback} />
);

const inviteNode = document.getElementById('mantine-invitation');
const inviteFallback = document.getElementById('invitation-fallback');
const inviteForm = inviteFallback?.querySelector('form');
if (inviteNode && inviteForm) mount(
  inviteNode, inviteFallback,
  <Invitation model={modelForm(inviteForm)} />
);
