import { Routes } from '@angular/router';
import { AuthGuard } from './auth/auth.guard';
import { AdminGuard } from './auth/admin.guard';
import { PublicGuard } from './auth/public.guard';

export const routes: Routes = [
    {
        path: 'search',
        loadComponent: () => import('./search-view/search-view.component').then(m => m.SearchViewComponent),
        canActivate: [PublicGuard]
    },
    {
        path: 'result',
        loadComponent: () => import('./result-view/result-view.component').then(m => m.ResultViewComponent),
        canActivate: [PublicGuard]
    },
    {
        path: 'contribute',
        loadComponent: () => import('./contribute-view/contribute-view.component').then(m => m.ContributeViewComponent),
        canActivate: [AuthGuard]
    },
    {
        path: 'contributions',
        loadComponent: () => import('./contributions-view/contributions-view.component').then(m => m.ContributionsViewComponent),
        canActivate: [AuthGuard]
    },
    {
        path: 'workflow/add-commentary',
        loadComponent: () => import('./add-commentary-workflow/add-commentary-workflow.component').then(m => m.AddCommentaryWorkflowComponent),
        canActivate: [AuthGuard]
    },
    {
        path: 'workflow/add-generictext',
        loadComponent: () => import('./add-generictext-workflow/add-generictext-workflow.component').then(m => m.AddGenerictextWorkflowComponent),
        canActivate: [AuthGuard]
    },
    {
        path: 'workflow/add-image',
        loadComponent: () => import('./add-image-workflow/add-image-workflow.component').then(m => m.AddImageWorkflowComponent),
        canActivate: [AuthGuard]
    },
    {
        path: 'login',
        loadComponent: () => import('./login/login-selector.component').then(m => m.LoginSelectorComponent)
    },
    {
        path: 'login/managed',
        loadComponent: () => import('./login/login.component').then(m => m.LoginComponent)
    },
    {
        path: 'about',
        loadComponent: () => import('./about/about.component').then(m => m.AboutComponent),
        canActivate: [PublicGuard]
    },
    {
        path: 'impressum',
        loadComponent: () => import('./impressum/impressum.component').then(m => m.ImpressumComponent),
        canActivate: [PublicGuard]
    },
    {
        path: 'datenschutz',
        loadComponent: () => import('./datenschutz/datenschutz.component').then(m => m.DatenschutzComponent),
        canActivate: [PublicGuard]
    },
    {
        path: 'nutzungsbedingungen',
        loadComponent: () => import('./nutzungsbedingungen/nutzungsbedingungen.component').then(m => m.NutzungsbedingungenComponent),
        canActivate: [PublicGuard]
    },
    {
        path: 'admin',
        loadComponent: () => import('./admin/admin-layout.component').then(m => m.AdminLayoutComponent),
        canActivate: [AdminGuard],
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
