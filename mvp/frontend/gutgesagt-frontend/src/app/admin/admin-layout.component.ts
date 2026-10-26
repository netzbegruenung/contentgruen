import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { MatIconModule } from '@angular/material/icon';
import { MatToolbarModule } from '@angular/material/toolbar';

@Component({
  selector: 'app-admin-layout',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatSidenavModule,
    MatListModule,
    MatIconModule,
    MatToolbarModule
  ],
  template: `
    <div class="admin-container">
      <!--
        Kein eigener Zurueck-Knopf: Der Pfeil im Kopf der App fuehrt von hier auf
        die Startseite (data.parent an der Route /admin). Zwei Pfeile nebeneinander
        mit demselben Ziel waren einer zu viel.
      -->
      <mat-toolbar color="primary" class="admin-toolbar">
        <span>🌱 Gut gesagt – Admin</span>
      </mat-toolbar>

      <mat-sidenav-container class="admin-sidenav-container">
        <mat-sidenav mode="side" opened class="admin-sidenav">
          <mat-nav-list>
            <a mat-list-item routerLink="/admin/dashboard" routerLinkActive="active">
              <mat-icon>dashboard</mat-icon>
              <span>MVP Dashboard</span>
            </a>
            <a mat-list-item routerLink="/admin/moderation" routerLinkActive="active">
              <mat-icon>flag</mat-icon>
              <span>Moderation</span>
            </a>
          </mat-nav-list>
        </mat-sidenav>

        <mat-sidenav-content class="admin-content">
          <router-outlet></router-outlet>
        </mat-sidenav-content>
      </mat-sidenav-container>
    </div>
  `,
  styles: [`
    .admin-container {
      height: 100vh;
      display: flex;
      flex-direction: column;
    }

    .admin-toolbar {
      position: sticky;
      top: 0;
      z-index: 100;
    }

    .spacer {
      flex: 1 1 auto;
    }

    .admin-sidenav-container {
      flex: 1;
    }

    .admin-sidenav {
      width: 250px;
      padding-top: 20px;
    }

    .admin-sidenav mat-icon {
      margin-right: 12px;
    }

    .admin-sidenav .active {
      background-color: rgba(0, 0, 0, 0.04);
    }

    .admin-content {
      padding: 20px;
      background-color: #f5f5f5;
    }

    @media (max-width: 768px) {
      .admin-sidenav {
        width: 200px;
      }
    }
  `]
})
export class AdminLayoutComponent {}
