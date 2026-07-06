import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDividerModule } from '@angular/material/divider';
import { UserInfo } from '../../../auth/auth.service';

@Component({
  selector: 'app-mobile-menu',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatDividerModule
  ],
  templateUrl: './mobile-menu.html',
  styleUrl: './mobile-menu.css'
})
export class MobileMenuComponent {
  @Input() userInfo: UserInfo | null = null;
  @Input() selectedProfilePictureUrl: string = '';

  @Output() closeMenu = new EventEmitter<void>();
  @Output() contribute = new EventEmitter<void>();
  @Output() contributions = new EventEmitter<void>();
  @Output() login = new EventEmitter<void>();
  @Output() loginToContribute = new EventEmitter<void>();
  @Output() logout = new EventEmitter<void>();
  @Output() help = new EventEmitter<void>();

  close(): void {
    this.closeMenu.emit();
  }

  onContributeClick(): void {
    this.contribute.emit();
    this.close();
  }

  onContributionsClick(): void {
    this.contributions.emit();
    this.close();
  }

  onLoginClick(): void {
    this.login.emit();
    this.close();
  }

  onLoginToContributeClick(): void {
    this.loginToContribute.emit();
    this.close();
  }

  onLogoutClick(): void {
    this.logout.emit();
    this.close();
  }

  onHelpClick(): void {
    this.help.emit();
    this.close();
  }
}
