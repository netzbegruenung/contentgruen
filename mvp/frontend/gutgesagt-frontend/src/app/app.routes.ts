import { ActivatedRouteSnapshot, Routes } from '@angular/router';
import { AuthGuard } from './auth/auth.guard';
import { AdminGuard } from './auth/admin.guard';
import { PublicGuard } from './auth/public.guard';
import { ShareTargetGuard } from './share-target/share-target.guard';
import { gespeichertEltern } from './beitragsformular/beitrag-gespeichert/gespeichert-adresse';

/**
 * Das Ziel des Zurueck-Pfeils: eine Ebene hoeher in der Hierarchie, nicht der
 * letzte Schritt der History. Entweder ein fester Pfad oder - wo das Ziel vom
 * Kontext abhaengt - eine Funktion ueber den Snapshot der Route.
 *
 * Der Pfeil im Kopf liest das ueber NavigationService.goBack(); das System-Zurueck
 * (Browser, Android-Geste) bleibt davon unberuehrt und folgt weiter der History.
 */
export type ElternZiel = string | ((snapshot: ActivatedRouteSnapshot) => string | unknown[]);

/**
 * Query-Parameter, die einen Unter-Screen auf derselben Seite bezeichnen
 * (``data.schliesst``). Ist einer davon gesetzt, schliesst der Pfeil zuerst ihn,
 * statt die Seite zu verlassen - erst der zweite Tipp geht eine Ebene hoch.
 *
 * Derzeit traegt keine Route das: Der einzige Nutzer war ``?form=`` auf
 * /contribute, und die Formulare sind inzwischen eigene Seiten. Die Mechanik im
 * NavigationService bleibt fuer den naechsten Unter-Screen.
 */
export type SchliesstParameter = string[];

/**
 * Beitragsformulare: Aus dem Destillier-Ablauf heraus fuehrt der Pfeil zurueck zum
 * Einwurf, sonst auf die Beitragen-Seite.
 *
 * Der Parametername steht hier als Literal statt als Import aus dem
 * Destillier-Dienst - die Routentabelle wird beim Start geladen und soll den
 * Dienst nicht ins erste Buendel ziehen. Beide Stellen tragen denselben Namen:
 * ROHINPUT_PARAM in destillier-uebergabe.service.ts.
 */
function formularEltern(snapshot: ActivatedRouteSnapshot): string | unknown[] {
  const rohinput = snapshot.queryParamMap.get('rohinput');
  return rohinput ? ['/destillieren', rohinput] : '/contribute';
}

/**
 * Einwerfen: Der Pfeil fuehrt auf die Beitragen-Seite - dort steht das Einwerfen als
 * erster Schritt der Kette, und von dort kommt der haeufigste Weg hierher (Kachel,
 * Menue, Knopf im Kopf).
 *
 * Ausnahme ist der FAB im Fangkorb: Wer dort einwirft, will zurueck in die Liste, in
 * der der Einwurf gleich liegt. Der FAB sagt das ueber ``?von=fangkorb``
 * (zumEinwerfen in raw-input-list.component.ts).
 */
function einwerfenEltern(snapshot: ActivatedRouteSnapshot): string {
  return snapshot.queryParamMap.get('von') === 'fangkorb' ? '/fangkorb' : '/contribute';
}

export const routes: Routes = [
    {
        path: 'search',
        loadComponent: () => import('./search-view/search-view.component').then(m => m.SearchViewComponent),
        canActivate: [PublicGuard]
        // Die Startseite selbst hat kein Elternziel und keinen Pfeil.
    },
    {
        path: 'result',
        loadComponent: () => import('./result-view/result-view.component').then(m => m.ResultViewComponent),
        canActivate: [PublicGuard],
        data: { parent: '/search' }
    },
    {
        // Nur Uebersicht. Die alten Adressen ?form= und ?panel= leitet die Seite
        // selbst ins Formular weiter (contribute-view.component.ts, ngOnInit).
        path: 'contribute',
        loadComponent: () => import('./contribute-view/contribute-view.component').then(m => m.ContributeViewComponent),
        canActivate: [AuthGuard],
        data: { parent: '/search' }
    },
    {
        path: 'einwerfen',
        loadComponent: () => import('./add-raw-input/add-raw-input.component').then(m => m.AddRawInputComponent),
        canActivate: [AuthGuard],
        data: { parent: einwerfenEltern }
    },
    {
        path: 'fangkorb',
        loadComponent: () => import('./raw-input-list/raw-input-list.component').then(m => m.RawInputListComponent),
        canActivate: [AuthGuard],
        data: { parent: '/search' }
    },
    {
        // Ohne ID: oeffnet den naechsten offenen Einwurf oder zeigt "Alles destilliert".
        path: 'destillieren',
        loadComponent: () => import('./destillieren/destillieren.component').then(m => m.DestillierenComponent),
        canActivate: [AuthGuard],
        data: { parent: '/fangkorb' }
    },
    {
        path: 'destillieren/:id',
        loadComponent: () => import('./destillieren/destillieren.component').then(m => m.DestillierenComponent),
        canActivate: [AuthGuard],
        data: { parent: '/fangkorb' }
    },
    {
        path: 'contributions',
        loadComponent: () => import('./contributions-view/contributions-view.component').then(m => m.ContributionsViewComponent),
        canActivate: [AuthGuard],
        data: { parent: '/search' }
    },
    {
        path: 'workflow/add-commentary',
        loadComponent: () => import('./add-commentary-workflow/add-commentary-workflow.component').then(m => m.AddCommentaryWorkflowComponent),
        canActivate: [AuthGuard],
        data: { parent: formularEltern }
    },
    {
        // Nach dem Speichern; der Pfeil fuehrt dorthin, woher das Formular kam, nicht zurueck hinein.
        path: 'workflow/add-commentary/gespeichert/:id',
        loadComponent: () => import('./beitragsformular/beitrag-gespeichert/beitrag-gespeichert.component').then(m => m.BeitragGespeichertComponent),
        canActivate: [AuthGuard],
        data: { parent: gespeichertEltern, typ: 'commentary' }
    },
    {
        path: 'workflow/add-generictext/gespeichert/:id',
        loadComponent: () => import('./beitragsformular/beitrag-gespeichert/beitrag-gespeichert.component').then(m => m.BeitragGespeichertComponent),
        canActivate: [AuthGuard],
        data: { parent: gespeichertEltern, typ: 'generictext' }
    },
    {
        path: 'workflow/add-generictext',
        loadComponent: () => import('./add-generictext-workflow/add-generictext-workflow.component').then(m => m.AddGenerictextWorkflowComponent),
        canActivate: [AuthGuard],
        data: { parent: formularEltern }
    },
    {
        path: 'workflow/add-image',
        loadComponent: () => import('./add-image-workflow/add-image-workflow.component').then(m => m.AddImageWorkflowComponent),
        canActivate: [AuthGuard],
        data: { parent: formularEltern }
    },
    {
        // Ziel des Android-Teilen-Menues (share_target im Manifest).
        //
        // Der Guard leitet ohne Zwischenseite auf /einwerfen weiter und legt die
        // geteilten Daten unterwegs ab; die Komponente hier wird nur gerendert,
        // wenn ?debug in der Adresse steht. Dass die Route ueberhaupt eine
        // Komponente hat, ist also der Diagnose-Fall, nicht der Normalfall.
        //
        // Ohne AuthGuard: den stellt /einwerfen, und weil die Nutzlast im
        // sessionStorage liegt statt in der Adresse, ueberlebt sie den Umweg
        // ueber /login von selbst.
        path: 'teilen',
        canActivate: [ShareTargetGuard],
        loadComponent: () => import('./share-target-debug/share-target-debug.component').then(m => m.ShareTargetDebugComponent),
        data: { parent: '/einwerfen' }
    },
    {
        path: 'login',
        loadComponent: () => import('./login/login-selector.component').then(m => m.LoginSelectorComponent),
        data: { parent: '/search' }
    },
    {
        path: 'login/managed',
        loadComponent: () => import('./login/login.component').then(m => m.LoginComponent),
        data: { parent: '/login' }
    },
    {
        path: 'about',
        loadComponent: () => import('./about/about.component').then(m => m.AboutComponent),
        canActivate: [PublicGuard],
        data: { parent: '/search' }
    },
    {
        path: 'impressum',
        loadComponent: () => import('./impressum/impressum.component').then(m => m.ImpressumComponent),
        canActivate: [PublicGuard],
        data: { parent: '/search' }
    },
    {
        path: 'datenschutz',
        loadComponent: () => import('./datenschutz/datenschutz.component').then(m => m.DatenschutzComponent),
        canActivate: [PublicGuard],
        data: { parent: '/search' }
    },
    {
        path: 'nutzungsbedingungen',
        loadComponent: () => import('./nutzungsbedingungen/nutzungsbedingungen.component').then(m => m.NutzungsbedingungenComponent),
        canActivate: [PublicGuard],
        data: { parent: '/search' }
    },
    {
        // Die Kinder erben das Elternziel: goBack sucht vom tiefsten Snapshot
        // aufwaerts, bis es eines findet.
        path: 'admin',
        loadComponent: () => import('./admin/admin-layout.component').then(m => m.AdminLayoutComponent),
        canActivate: [AdminGuard],
        data: { parent: '/search' },
        children: [
            {
                path: 'dashboard',
                loadComponent: () => import('./admin/mvp-dashboard/mvp-dashboard.component').then(m => m.MvpDashboardComponent)
            },
            {
                path: 'moderation',
                loadComponent: () => import('./admin/content-moderation/content-moderation.component').then(m => m.ContentModerationComponent)
            },
            {
                path: '',
                redirectTo: 'dashboard',
                pathMatch: 'full'
            }
        ]
    },
    { path: '', redirectTo: '/search', pathMatch: 'full' }, // Default route
    { path: '**', redirectTo: '/search' } // Fallback route - redirect to search for anonymous users
];
