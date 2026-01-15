/**
 * MTT Design System - Ant Design Vue Theme Configuration
 *
 * This file defines all theme tokens used across the application.
 * Using Ant Design's theming API instead of CSS overrides for stability.
 *
 * Note: Component-specific tokens that aren't typed are applied via CSS
 * in style.css as minimal overrides.
 *
 * @see https://antdv.com/docs/vue/customize-theme
 */

import type { ThemeConfig } from 'ant-design-vue/es/config-provider/context'
import { theme } from 'ant-design-vue'

/**
 * Brand colors - aligned with login page
 */
export const colors = {
  primary: '#3b82f6',
  primaryHover: '#2563eb',
  primaryActive: '#1d4ed8',

  // Semantic colors
  success: '#10B981',
  warning: '#F59E0B',
  error: '#EF4444',
  info: '#3B82F6',

  // Dark slate palette (for sidebar/header)
  slate900: '#0f172a',
  slate800: '#1e293b',
  slate700: '#334155',
  slate600: '#475569',

  // Light palette
  bgPage: '#F8FAFC',
  bgSubtle: '#F1F5F9',
  border: '#E2E8F0',
  borderLight: '#F1F5F9',
  text: '#1E293B',
  textSecondary: '#64748B',
  textMuted: '#94A3B8',
}

/**
 * Main application theme (light mode for content area)
 * Compact sizing for data-dense tables and forms
 */
export const appTheme: ThemeConfig = {
  token: {
    // Brand color
    colorPrimary: colors.primary,
    colorLink: colors.primary,
    colorLinkHover: colors.primaryHover,
    colorLinkActive: colors.primaryActive,

    // Status colors
    colorSuccess: colors.success,
    colorWarning: colors.warning,
    colorError: colors.error,
    colorInfo: colors.info,

    // Typography - compact scale
    fontSize: 13,
    fontSizeHeading1: 24,
    fontSizeHeading2: 20,
    fontSizeHeading3: 16,
    fontSizeHeading4: 14,
    fontSizeHeading5: 13,
    fontSizeLG: 14,
    fontSizeSM: 12,
    fontSizeXL: 16,

    // Spacing - compact
    padding: 12,
    paddingLG: 16,
    paddingSM: 8,
    paddingXS: 4,
    paddingXXS: 2,
    margin: 12,
    marginLG: 16,
    marginSM: 8,
    marginXS: 4,
    marginXXS: 2,

    // Border radius - compact
    borderRadius: 4,
    borderRadiusLG: 6,
    borderRadiusSM: 2,
    borderRadiusXS: 2,

    // Backgrounds
    colorBgContainer: '#FFFFFF',
    colorBgLayout: colors.bgPage,
    colorBgElevated: '#FFFFFF',

    // Borders
    colorBorder: colors.border,
    colorBorderSecondary: colors.borderLight,

    // Text
    colorText: colors.text,
    colorTextSecondary: colors.textSecondary,
    colorTextTertiary: colors.textMuted,
    colorTextQuaternary: colors.textMuted,

    // Control sizing - compact
    controlHeight: 32,
    controlHeightLG: 36,
    controlHeightSM: 24,

    // Line heights
    lineHeight: 1.4,
    lineHeightLG: 1.5,
    lineHeightSM: 1.3,

    // Box shadows - subtle
    boxShadow: '0 1px 2px rgba(0, 0, 0, 0.04)',
    boxShadowSecondary: '0 4px 6px -1px rgba(0, 0, 0, 0.08), 0 2px 4px -1px rgba(0, 0, 0, 0.04)',

    // Motion - fast for responsiveness
    motionDurationFast: '0.1s',
    motionDurationMid: '0.15s',
    motionDurationSlow: '0.25s',
  },
}

/**
 * Dark theme for sidebar navigation
 * Uses nested ConfigProvider with dark algorithm
 */
export const sidebarTheme: ThemeConfig = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: colors.primary,
    colorBgContainer: colors.slate800,
    colorBgElevated: colors.slate700,
    colorBgLayout: colors.slate800,
    colorBorder: colors.slate700,
    colorBorderSecondary: colors.slate700,
    fontSize: 12,
    borderRadius: 4,
  },
}
