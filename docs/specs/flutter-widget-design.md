# Flutter Widget Design Specification

> ⚠️ **ARCHIVED ALTERNATIVE** - January 2026
>
> This document describes a **Flutter-based approach** that was considered but **NOT chosen** for implementation.
>
> **Final Decision:** Extend the existing **Telegram Mini App** (React + TypeScript) instead.
>
> **Reason:** Full WiFi coverage in the yard eliminates the need for Flutter's offline capabilities. Using the existing Mini App means same tech stack, same team, and workers already use Telegram.
>
> **Active Design Document:** See `miniapp-placement-design.md` for the chosen implementation.

---

## MTT Mobile - Yard Manager Tablet Application

This document provides detailed Flutter widget implementations for the MTT Container Terminal mobile application, focusing on the 2D yard visualization system.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Core Models](#2-core-models)
3. [Theme & Constants](#3-theme--constants)
4. [2D Grid Visualization Widgets](#4-2d-grid-visualization-widgets)
5. [Work Order Widgets](#5-work-order-widgets)
6. [Placement Confirmation Widgets](#6-placement-confirmation-widgets)
7. [State Management](#7-state-management)
8. [Offline Support](#8-offline-support)
9. [API Integration](#9-api-integration)

---

## 1. Architecture Overview

### Project Structure

```
lib/
├── main.dart
├── app/
│   ├── app.dart                    # MaterialApp with theme
│   ├── routes.dart                 # GoRouter configuration
│   └── injection.dart              # Dependency injection (GetIt)
│
├── features/
│   ├── auth/                       # Authentication feature
│   ├── work_orders/                # Work order management
│   ├── placement/                  # 2D visualization & placement
│   └── photo/                      # Photo capture & upload
│
├── core/
│   ├── api/                        # API client (Dio)
│   ├── database/                   # Hive & SQLite
│   ├── sync/                       # Offline sync
│   └── notifications/              # FCM
│
└── shared/
    ├── widgets/                    # Reusable widgets
    ├── constants/                  # Colors, dimensions
    └── utils/                      # Formatters, helpers
```

### Dependencies (pubspec.yaml)

```yaml
name: mtt_mobile
description: MTT Container Terminal - Yard Manager App
version: 1.0.0+1

environment:
  sdk: '>=3.0.0 <4.0.0'
  flutter: '>=3.10.0'

dependencies:
  flutter:
    sdk: flutter

  # State Management (Riverpod 3.x - Jan 2026)
  flutter_riverpod: ^3.1.0
  riverpod_annotation: ^4.0.0

  # Navigation
  go_router: ^17.0.1

  # Network
  dio: ^5.9.0
  web_socket_channel: ^3.0.0
  connectivity_plus: ^7.0.0

  # Local Storage
  # Note: Consider hive_ce (Community Edition) for better Dart 3 support
  hive: ^2.2.3
  hive_flutter: ^1.1.0
  sqflite: ^2.4.0

  # UI Components
  flutter_svg: ^2.0.10
  cached_network_image: ^3.4.0
  shimmer: ^3.0.0

  # Camera & Photos
  camera: ^0.11.3
  image_picker: ^1.1.0
  image: ^4.3.0

  # Notifications
  firebase_core: ^3.8.0
  firebase_messaging: ^16.1.0
  flutter_local_notifications: ^18.0.0

  # Utilities
  intl: ^0.20.0
  freezed_annotation: ^3.0.0
  json_annotation: ^4.9.0
  uuid: ^4.5.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  build_runner: ^2.4.13
  freezed: ^3.2.4
  json_serializable: ^6.9.0
  riverpod_generator: ^4.0.0
  flutter_lints: ^5.0.0
```

---

## 2. Core Models

### Position Model

```dart
// lib/features/placement/models/position.dart

import 'package:freezed_annotation/freezed_annotation.dart';

part 'position.freezed.dart';
part 'position.g.dart';

/// Represents a position in the terminal yard
/// Format: Zone-Row-Bay-Tier-SubSlot (e.g., A-R03-B15-T2-A)
@freezed
class Position with _$Position {
  const Position._();

  const factory Position({
    required String zone,
    required int row,
    required int bay,
    required int tier,
    @Default('A') String subSlot,
  }) = _Position;

  factory Position.fromJson(Map<String, dynamic> json) =>
      _$PositionFromJson(json);

  /// Parse from coordinate string: "A-R03-B15-T2-A"
  factory Position.fromCoordinate(String coord) {
    final parts = coord.split('-');
    return Position(
      zone: parts[0],
      row: int.parse(parts[1].replaceAll('R', '')),
      bay: int.parse(parts[2].replaceAll('B', '')),
      tier: int.parse(parts[3].replaceAll('T', '')),
      subSlot: parts.length > 4 ? parts[4] : 'A',
    );
  }

  /// Convert to coordinate string
  String toCoordinate() =>
      '$zone-R${row.toString().padLeft(2, '0')}-B${bay.toString().padLeft(2, '0')}-T$tier-$subSlot';

  /// Short display format for UI
  String toShortString() => '$zone-R$row-B$bay-T$tier';
}
```

### Work Order Model

```dart
// lib/features/work_orders/models/work_order.dart

import 'package:freezed_annotation/freezed_annotation.dart';
import '../../placement/models/position.dart';

part 'work_order.freezed.dart';
part 'work_order.g.dart';

enum WorkOrderStatus {
  pending,
  assigned,
  accepted,
  inProgress,
  completed,
  verified,
  flagged,
  cancelled,
}

enum WorkOrderPriority {
  low,
  normal,
  high,
  urgent,
}

enum ContainerSize {
  ft20,
  ft40,
  ft45,
}

enum ContainerStatus {
  laden,
  empty,
}

@freezed
class WorkOrder with _$WorkOrder {
  const WorkOrder._();

  const factory WorkOrder({
    required String id,
    required String orderNumber,
    required String containerNumber,
    required ContainerSize containerSize,
    required ContainerStatus containerStatus,
    required double? weight,
    required String customerName,
    required Position targetPosition,
    required WorkOrderStatus status,
    required WorkOrderPriority priority,
    required DateTime createdAt,
    required DateTime slaDeadline,
    DateTime? acceptedAt,
    DateTime? completedAt,
    String? containerBelow,
    String? sealNumber,
    String? notes,
  }) = _WorkOrder;

  factory WorkOrder.fromJson(Map<String, dynamic> json) =>
      _$WorkOrderFromJson(json);

  /// Time remaining until SLA deadline
  Duration get timeRemaining => slaDeadline.difference(DateTime.now());

  /// Whether SLA is breached
  bool get isOverdue => timeRemaining.isNegative;

  /// Whether SLA is at risk (less than 20% time remaining)
  bool get isAtRisk {
    final total = slaDeadline.difference(createdAt);
    return timeRemaining < total * 0.2;
  }

  /// Container size display string
  String get sizeDisplay {
    switch (containerSize) {
      case ContainerSize.ft20:
        return '20ft';
      case ContainerSize.ft40:
        return '40ft';
      case ContainerSize.ft45:
        return '45ft';
    }
  }

  /// Status display in Russian
  String get statusDisplayRu {
    switch (containerStatus) {
      case ContainerStatus.laden:
        return 'ГРУЖ';
      case ContainerStatus.empty:
        return 'ПОРОЖ';
    }
  }
}
```

### Yard Layout Model

```dart
// lib/features/placement/models/yard_layout.dart

import 'package:freezed_annotation/freezed_annotation.dart';

part 'yard_layout.freezed.dart';
part 'yard_layout.g.dart';

/// Represents a single cell in the yard grid
@freezed
class YardCell with _$YardCell {
  const YardCell._();

  const factory YardCell({
    required int row,
    required int bay,
    required int currentTier,    // Current stack height (0-4)
    required int maxTier,        // Max allowed tier (usually 4)
    String? topContainerId,      // Container on top of stack
    @Default(false) bool isTarget,
    @Default(false) bool isHighlighted,
  }) = _YardCell;

  factory YardCell.fromJson(Map<String, dynamic> json) =>
      _$YardCellFromJson(json);

  /// Whether this cell can accept more containers
  bool get canStack => currentTier < maxTier;

  /// Number of additional containers that can be stacked
  int get availableTiers => maxTier - currentTier;
}

/// Represents the full yard layout for a zone
@freezed
class YardLayout with _$YardLayout {
  const factory YardLayout({
    required String zone,
    required int maxRows,
    required int maxBays,
    required int maxTiers,
    required List<YardCell> cells,
    required Map<String, int> occupancyByRow,
  }) = _YardLayout;

  factory YardLayout.fromJson(Map<String, dynamic> json) =>
      _$YardLayoutFromJson(json);
}
```

---

## 3. Theme & Constants

### Colors

```dart
// lib/shared/constants/colors.dart

import 'package:flutter/material.dart';

/// MTT Brand Colors
class MttColors {
  MttColors._();

  // Primary
  static const primary = Color(0xFF1890FF);
  static const primaryDark = Color(0xFF003EB3);
  static const primaryLight = Color(0xFF40A9FF);

  // Status Colors
  static const success = Color(0xFF52C41A);
  static const warning = Color(0xFFFAAD14);
  static const error = Color(0xFFF5222D);
  static const info = Color(0xFF1890FF);

  // Container Status
  static const laden = Color(0xFF52C41A);      // Green for laden
  static const empty = Color(0xFF1890FF);      // Blue for empty

  // Priority Colors
  static const priorityLow = Color(0xFF8C8C8C);
  static const priorityNormal = Color(0xFF1890FF);
  static const priorityHigh = Color(0xFFFAAD14);
  static const priorityUrgent = Color(0xFFF5222D);

  // Grid Cell Colors (by tier count)
  static const cellEmpty = Color(0xFFE8E8E8);      // No containers
  static const cellTier1 = Color(0xFF95DE64);      // 1 tier - light green
  static const cellTier2 = Color(0xFF52C41A);      // 2 tiers - green
  static const cellTier3 = Color(0xFFFFA940);      // 3 tiers - orange
  static const cellTier4 = Color(0xFFFF4D4F);      // 4 tiers (full) - red
  static const cellTarget = Color(0xFFFAAD14);     // Target position - gold

  // Side View
  static const containerFilled = Color(0xFF434343);
  static const containerTarget = Color(0xFFFAAD14);
  static const tierLine = Color(0xFFD9D9D9);

  // Background
  static const background = Color(0xFFF5F5F5);
  static const surface = Color(0xFFFFFFFF);
  static const surfaceVariant = Color(0xFFFAFAFA);

  // Text
  static const textPrimary = Color(0xFF262626);
  static const textSecondary = Color(0xFF8C8C8C);
  static const textDisabled = Color(0xFFBFBFBF);

  /// Get cell color based on tier count
  static Color getCellColor(int tierCount, {bool isTarget = false}) {
    if (isTarget) return cellTarget;

    switch (tierCount) {
      case 0:
        return cellEmpty;
      case 1:
        return cellTier1;
      case 2:
        return cellTier2;
      case 3:
        return cellTier3;
      case 4:
      default:
        return cellTier4;
    }
  }

  /// Get priority color
  static Color getPriorityColor(WorkOrderPriority priority) {
    switch (priority) {
      case WorkOrderPriority.low:
        return priorityLow;
      case WorkOrderPriority.normal:
        return priorityNormal;
      case WorkOrderPriority.high:
        return priorityHigh;
      case WorkOrderPriority.urgent:
        return priorityUrgent;
    }
  }
}
```

### Dimensions

```dart
// lib/shared/constants/dimensions.dart

/// Grid and layout dimensions
class MttDimensions {
  MttDimensions._();

  // Grid Cell Sizes
  static const double cellSize = 48.0;          // Grid cell size
  static const double cellSpacing = 2.0;        // Space between cells
  static const double cellBorderRadius = 4.0;
  static const double cellBorderWidth = 1.0;

  // Side View
  static const double sideViewHeight = 160.0;
  static const double sideViewCellWidth = 60.0;
  static const double sideViewTierHeight = 36.0;

  // Labels
  static const double rowLabelWidth = 40.0;
  static const double bayLabelHeight = 24.0;

  // Terminal Layout
  static const int maxRows = 10;
  static const int maxBays = 10;
  static const int maxTiers = 4;

  // Row Segregation
  static const List<int> rows40ft = [1, 2, 3, 4, 5];
  static const List<int> rows20ft = [6, 7, 8, 9, 10];

  // Padding
  static const double screenPadding = 16.0;
  static const double cardPadding = 12.0;
  static const double sectionSpacing = 16.0;

  // Card
  static const double cardBorderRadius = 8.0;
  static const double cardElevation = 2.0;
}
```

### Theme

```dart
// lib/app/theme.dart

import 'package:flutter/material.dart';
import '../shared/constants/colors.dart';

class MttTheme {
  MttTheme._();

  static ThemeData get light => ThemeData(
    useMaterial3: true,
    colorScheme: ColorScheme.light(
      primary: MttColors.primary,
      secondary: MttColors.primaryLight,
      surface: MttColors.surface,
      background: MttColors.background,
      error: MttColors.error,
    ),
    scaffoldBackgroundColor: MttColors.background,
    appBarTheme: const AppBarTheme(
      backgroundColor: MttColors.surface,
      foregroundColor: MttColors.textPrimary,
      elevation: 1,
      centerTitle: true,
    ),
    cardTheme: CardTheme(
      color: MttColors.surface,
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
      ),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: ElevatedButton.styleFrom(
        backgroundColor: MttColors.primary,
        foregroundColor: Colors.white,
        minimumSize: const Size(double.infinity, 48),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
        ),
      ),
    ),
    textTheme: const TextTheme(
      headlineLarge: TextStyle(
        fontSize: 24,
        fontWeight: FontWeight.bold,
        color: MttColors.textPrimary,
      ),
      headlineMedium: TextStyle(
        fontSize: 20,
        fontWeight: FontWeight.w600,
        color: MttColors.textPrimary,
      ),
      titleLarge: TextStyle(
        fontSize: 18,
        fontWeight: FontWeight.w600,
        color: MttColors.textPrimary,
      ),
      titleMedium: TextStyle(
        fontSize: 16,
        fontWeight: FontWeight.w500,
        color: MttColors.textPrimary,
      ),
      bodyLarge: TextStyle(
        fontSize: 16,
        color: MttColors.textPrimary,
      ),
      bodyMedium: TextStyle(
        fontSize: 14,
        color: MttColors.textPrimary,
      ),
      bodySmall: TextStyle(
        fontSize: 12,
        color: MttColors.textSecondary,
      ),
    ),
  );
}
```

---

## 4. 2D Grid Visualization Widgets

### Yard Grid View (Main Component)

```dart
// lib/features/placement/widgets/yard_grid_view.dart

import 'package:flutter/material.dart';
import '../models/yard_layout.dart';
import '../models/position.dart';
import '../../../shared/constants/colors.dart';
import '../../../shared/constants/dimensions.dart';
import 'position_cell.dart';

/// Top-down 2D grid view of the terminal yard
class YardGridView extends StatelessWidget {
  const YardGridView({
    super.key,
    required this.layout,
    required this.targetPosition,
    this.visibleRows,
    this.visibleBays,
    this.onCellTap,
  });

  final YardLayout layout;
  final Position targetPosition;
  final List<int>? visibleRows;    // Optional: filter visible rows
  final List<int>? visibleBays;    // Optional: filter visible bays
  final void Function(int row, int bay)? onCellTap;

  @override
  Widget build(BuildContext context) {
    final rows = visibleRows ??
        List.generate(layout.maxRows, (i) => i + 1);
    final bays = visibleBays ??
        List.generate(layout.maxBays, (i) => i + 1);

    return InteractiveViewer(
      constrained: false,
      boundaryMargin: const EdgeInsets.all(100),
      minScale: 0.5,
      maxScale: 3.0,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Bay labels header
          _buildBayLabels(bays),
          const SizedBox(height: MttDimensions.cellSpacing),

          // Grid rows
          ...rows.map((row) => Padding(
            padding: const EdgeInsets.only(
              bottom: MttDimensions.cellSpacing,
            ),
            child: _buildGridRow(row, bays),
          )),
        ],
      ),
    );
  }

  Widget _buildBayLabels(List<int> bays) {
    return Row(
      children: [
        // Empty space for row labels
        const SizedBox(width: MttDimensions.rowLabelWidth),
        const SizedBox(width: MttDimensions.cellSpacing),

        // Bay labels
        ...bays.map((bay) => Container(
          width: MttDimensions.cellSize,
          height: MttDimensions.bayLabelHeight,
          margin: const EdgeInsets.only(
            right: MttDimensions.cellSpacing,
          ),
          alignment: Alignment.center,
          child: Text(
            'B${bay.toString().padLeft(2, '0')}',
            style: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: MttColors.textSecondary,
            ),
          ),
        )),
      ],
    );
  }

  Widget _buildGridRow(int row, List<int> bays) {
    return Row(
      children: [
        // Row label
        Container(
          width: MttDimensions.rowLabelWidth,
          height: MttDimensions.cellSize,
          alignment: Alignment.center,
          child: Text(
            'R${row.toString().padLeft(2, '0')}',
            style: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: MttColors.textSecondary,
            ),
          ),
        ),
        const SizedBox(width: MttDimensions.cellSpacing),

        // Cells for this row
        ...bays.map((bay) {
          final cell = _getCellAt(row, bay);
          final isTarget = targetPosition.row == row &&
                          targetPosition.bay == bay;

          return Padding(
            padding: const EdgeInsets.only(
              right: MttDimensions.cellSpacing,
            ),
            child: PositionCell(
              row: row,
              bay: bay,
              tierCount: cell?.currentTier ?? 0,
              targetTier: isTarget ? targetPosition.tier : null,
              isTarget: isTarget,
              onTap: onCellTap != null
                  ? () => onCellTap!(row, bay)
                  : null,
            ),
          );
        }),
      ],
    );
  }

  YardCell? _getCellAt(int row, int bay) {
    try {
      return layout.cells.firstWhere(
        (c) => c.row == row && c.bay == bay,
      );
    } catch (_) {
      return null;
    }
  }
}
```

### Position Cell Widget

```dart
// lib/features/placement/widgets/position_cell.dart

import 'package:flutter/material.dart';
import '../../../shared/constants/colors.dart';
import '../../../shared/constants/dimensions.dart';

/// Individual cell in the yard grid
class PositionCell extends StatelessWidget {
  const PositionCell({
    super.key,
    required this.row,
    required this.bay,
    required this.tierCount,
    this.targetTier,
    this.isTarget = false,
    this.onTap,
  });

  final int row;
  final int bay;
  final int tierCount;       // Current stack height (0-4)
  final int? targetTier;     // If this is target, which tier?
  final bool isTarget;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final color = MttColors.getCellColor(tierCount, isTarget: isTarget);
    final borderColor = isTarget
        ? MttColors.cellTarget
        : Colors.transparent;

    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        width: MttDimensions.cellSize,
        height: MttDimensions.cellSize,
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(
            MttDimensions.cellBorderRadius,
          ),
          border: Border.all(
            color: borderColor,
            width: isTarget ? 3.0 : 1.0,
          ),
          boxShadow: isTarget
              ? [
                  BoxShadow(
                    color: MttColors.cellTarget.withOpacity(0.4),
                    blurRadius: 8,
                    spreadRadius: 2,
                  ),
                ]
              : null,
        ),
        child: Center(
          child: _buildContent(),
        ),
      ),
    );
  }

  Widget _buildContent() {
    if (isTarget && targetTier != null) {
      // Target cell: show target icon and tier
      return Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(
            Icons.location_on,
            size: 16,
            color: Colors.white,
          ),
          Text(
            'T$targetTier',
            style: const TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.bold,
              color: Colors.white,
            ),
          ),
        ],
      );
    } else if (tierCount > 0) {
      // Occupied cell: show tier count
      return Text(
        tierCount.toString(),
        style: TextStyle(
          fontSize: 16,
          fontWeight: FontWeight.bold,
          color: tierCount >= 3 ? Colors.white : MttColors.textPrimary,
        ),
      );
    } else {
      // Empty cell
      return const SizedBox.shrink();
    }
  }
}
```

### Row Side View Widget

```dart
// lib/features/placement/widgets/row_side_view.dart

import 'package:flutter/material.dart';
import '../models/yard_layout.dart';
import '../models/position.dart';
import '../../../shared/constants/colors.dart';
import '../../../shared/constants/dimensions.dart';

/// Cross-section (side) view of a single row
/// Shows vertical stacking of containers
class RowSideView extends StatelessWidget {
  const RowSideView({
    super.key,
    required this.layout,
    required this.targetPosition,
    this.visibleBays,
  });

  final YardLayout layout;
  final Position targetPosition;
  final List<int>? visibleBays;

  @override
  Widget build(BuildContext context) {
    final bays = visibleBays ??
        List.generate(layout.maxBays, (i) => i + 1);

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: MttColors.surface,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: MttColors.tierLine),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Text(
            'Ряд ${targetPosition.row.toString().padLeft(2, '0')} - Вид сбоку',
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: MttColors.textPrimary,
            ),
          ),
          const SizedBox(height: 12),

          // Side view grid
          SizedBox(
            height: MttDimensions.sideViewHeight,
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                // Tier labels
                _buildTierLabels(),
                const SizedBox(width: 8),

                // Bay columns
                Expanded(
                  child: SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: bays.map((bay) {
                        final cell = _getCellAt(targetPosition.row, bay);
                        final isTargetBay = targetPosition.bay == bay;

                        return _buildBayColumn(
                          bay: bay,
                          currentTier: cell?.currentTier ?? 0,
                          targetTier: isTargetBay
                              ? targetPosition.tier
                              : null,
                          isTarget: isTargetBay,
                        );
                      }).toList(),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTierLabels() {
    return Column(
      mainAxisAlignment: MainAxisAlignment.end,
      children: List.generate(layout.maxTiers, (i) {
        final tier = layout.maxTiers - i;
        return SizedBox(
          height: MttDimensions.sideViewTierHeight,
          child: Align(
            alignment: Alignment.centerRight,
            child: Text(
              'T$tier',
              style: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w500,
                color: MttColors.textSecondary,
              ),
            ),
          ),
        );
      }),
    );
  }

  Widget _buildBayColumn({
    required int bay,
    required int currentTier,
    int? targetTier,
    bool isTarget = false,
  }) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.end,
      children: [
        // Tier cells (from top to bottom)
        ...List.generate(layout.maxTiers, (i) {
          final tier = layout.maxTiers - i;
          final isFilled = tier <= currentTier;
          final isTargetCell = isTarget && tier == targetTier;

          return Container(
            width: MttDimensions.sideViewCellWidth,
            height: MttDimensions.sideViewTierHeight,
            margin: const EdgeInsets.symmetric(horizontal: 2),
            decoration: BoxDecoration(
              color: isTargetCell
                  ? MttColors.cellTarget
                  : isFilled
                      ? MttColors.containerFilled
                      : Colors.transparent,
              border: Border.all(
                color: MttColors.tierLine,
                width: 1,
              ),
              borderRadius: BorderRadius.circular(2),
            ),
            child: isTargetCell
                ? const Center(
                    child: Icon(
                      Icons.arrow_downward,
                      size: 20,
                      color: Colors.white,
                    ),
                  )
                : null,
          );
        }),

        // Bay label
        const SizedBox(height: 4),
        Text(
          'B${bay.toString().padLeft(2, '0')}',
          style: TextStyle(
            fontSize: 10,
            fontWeight: isTarget ? FontWeight.bold : FontWeight.normal,
            color: isTarget
                ? MttColors.cellTarget
                : MttColors.textSecondary,
          ),
        ),
      ],
    );
  }

  YardCell? _getCellAt(int row, int bay) {
    try {
      return layout.cells.firstWhere(
        (c) => c.row == row && c.bay == bay,
      );
    } catch (_) {
      return null;
    }
  }
}
```

### Placement Map Screen (Combined View)

```dart
// lib/features/placement/screens/placement_map_screen.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/work_order.dart';
import '../models/yard_layout.dart';
import '../widgets/yard_grid_view.dart';
import '../widgets/row_side_view.dart';
import '../widgets/container_info_card.dart';
import '../widgets/stacking_warning.dart';
import '../providers/placement_provider.dart';
import '../../../shared/constants/colors.dart';
import '../../../shared/constants/dimensions.dart';

class PlacementMapScreen extends ConsumerWidget {
  const PlacementMapScreen({
    super.key,
    required this.workOrder,
  });

  final WorkOrder workOrder;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final layoutAsync = ref.watch(yardLayoutProvider(workOrder.targetPosition.zone));

    return Scaffold(
      appBar: AppBar(
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.of(context).pop(),
        ),
        title: Text(workOrder.orderNumber),
        actions: [
          IconButton(
            icon: const Icon(Icons.my_location),
            onPressed: () {
              // TODO: Center on target
            },
          ),
        ],
      ),
      body: layoutAsync.when(
        loading: () => const Center(
          child: CircularProgressIndicator(),
        ),
        error: (error, stack) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, size: 48, color: MttColors.error),
              const SizedBox(height: 16),
              Text('Ошибка загрузки: $error'),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: () => ref.refresh(yardLayoutProvider(
                  workOrder.targetPosition.zone,
                )),
                child: const Text('Повторить'),
              ),
            ],
          ),
        ),
        data: (layout) => _buildContent(context, layout),
      ),
      bottomNavigationBar: _buildBottomBar(context),
    );
  }

  Widget _buildContent(BuildContext context, YardLayout layout) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(MttDimensions.screenPadding),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Zone header
          _buildZoneHeader(),
          const SizedBox(height: MttDimensions.sectionSpacing),

          // Top-down grid view
          Card(
            child: Padding(
              padding: const EdgeInsets.all(MttDimensions.cardPadding),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Вид сверху',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 12),
                  SizedBox(
                    height: 300,
                    child: YardGridView(
                      layout: layout,
                      targetPosition: workOrder.targetPosition,
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: MttDimensions.sectionSpacing),

          // Side view
          RowSideView(
            layout: layout,
            targetPosition: workOrder.targetPosition,
          ),
          const SizedBox(height: MttDimensions.sectionSpacing),

          // Container info
          ContainerInfoCard(workOrder: workOrder),
          const SizedBox(height: MttDimensions.sectionSpacing),

          // Stacking warning (if tier > 1)
          if (workOrder.targetPosition.tier > 1)
            StackingWarning(
              containerBelow: workOrder.containerBelow,
              targetTier: workOrder.targetPosition.tier,
            ),

          // Bottom padding for button
          const SizedBox(height: 80),
        ],
      ),
    );
  }

  Widget _buildZoneHeader() {
    return Row(
      children: [
        Container(
          padding: const EdgeInsets.symmetric(
            horizontal: 12,
            vertical: 6,
          ),
          decoration: BoxDecoration(
            color: MttColors.primary,
            borderRadius: BorderRadius.circular(4),
          ),
          child: Text(
            'ЗОНА ${workOrder.targetPosition.zone}',
            style: const TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.bold,
              color: Colors.white,
            ),
          ),
        ),
        const SizedBox(width: 12),
        Text(
          workOrder.targetPosition.toShortString(),
          style: const TextStyle(
            fontSize: 18,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }

  Widget _buildBottomBar(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(MttDimensions.screenPadding),
      decoration: const BoxDecoration(
        color: MttColors.surface,
        boxShadow: [
          BoxShadow(
            color: Colors.black12,
            blurRadius: 4,
            offset: Offset(0, -2),
          ),
        ],
      ),
      child: SafeArea(
        child: ElevatedButton.icon(
          onPressed: () {
            Navigator.of(context).pushNamed(
              '/confirm-placement',
              arguments: workOrder,
            );
          },
          icon: const Icon(Icons.play_arrow),
          label: const Text('НАЧАТЬ РАЗМЕЩЕНИЕ'),
          style: ElevatedButton.styleFrom(
            backgroundColor: MttColors.success,
            padding: const EdgeInsets.symmetric(vertical: 16),
          ),
        ),
      ),
    );
  }
}
```

### Grid Legend Widget

```dart
// lib/features/placement/widgets/grid_legend.dart

import 'package:flutter/material.dart';
import '../../../shared/constants/colors.dart';

/// Legend explaining grid cell colors
class GridLegend extends StatelessWidget {
  const GridLegend({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: MttColors.surfaceVariant,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Легенда',
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: MttColors.textSecondary,
            ),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 16,
            runSpacing: 8,
            children: [
              _buildLegendItem(MttColors.cellEmpty, 'Пусто'),
              _buildLegendItem(MttColors.cellTier1, '1 ярус'),
              _buildLegendItem(MttColors.cellTier2, '2 яруса'),
              _buildLegendItem(MttColors.cellTier3, '3 яруса'),
              _buildLegendItem(MttColors.cellTier4, 'Полный'),
              _buildLegendItem(MttColors.cellTarget, 'Цель', isTarget: true),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildLegendItem(Color color, String label, {bool isTarget = false}) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 16,
          height: 16,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(2),
            border: isTarget
                ? Border.all(color: color, width: 2)
                : null,
          ),
          child: isTarget
              ? const Icon(Icons.location_on, size: 10, color: Colors.white)
              : null,
        ),
        const SizedBox(width: 4),
        Text(
          label,
          style: const TextStyle(
            fontSize: 11,
            color: MttColors.textSecondary,
          ),
        ),
      ],
    );
  }
}
```

---

## 5. Work Order Widgets

### Work Order Card

```dart
// lib/features/work_orders/widgets/work_order_card.dart

import 'package:flutter/material.dart';
import '../models/work_order.dart';
import '../../../shared/constants/colors.dart';
import 'priority_badge.dart';
import 'countdown_timer.dart';

class WorkOrderCard extends StatelessWidget {
  const WorkOrderCard({
    super.key,
    required this.workOrder,
    required this.onAccept,
    required this.onDecline,
    this.onTap,
  });

  final WorkOrder workOrder;
  final VoidCallback onAccept;
  final VoidCallback onDecline;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header row
              Row(
                children: [
                  PriorityBadge(priority: workOrder.priority),
                  const SizedBox(width: 8),
                  Text(
                    workOrder.orderNumber,
                    style: const TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const Spacer(),
                  CountdownTimer(deadline: workOrder.slaDeadline),
                ],
              ),
              const SizedBox(height: 12),

              // Container info
              Row(
                children: [
                  const Icon(Icons.inventory_2, size: 18, color: MttColors.textSecondary),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      '${workOrder.containerNumber} → ${workOrder.targetPosition.toShortString()}',
                      style: const TextStyle(
                        fontSize: 15,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),

              // Size and status
              Row(
                children: [
                  _buildTag(
                    workOrder.sizeDisplay,
                    MttColors.textSecondary,
                  ),
                  const SizedBox(width: 8),
                  _buildTag(
                    workOrder.statusDisplayRu,
                    workOrder.containerStatus == ContainerStatus.laden
                        ? MttColors.laden
                        : MttColors.empty,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      workOrder.customerName,
                      style: const TextStyle(
                        fontSize: 13,
                        color: MttColors.textSecondary,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              // Action buttons
              Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: onDecline,
                      style: OutlinedButton.styleFrom(
                        foregroundColor: MttColors.error,
                        side: const BorderSide(color: MttColors.error),
                      ),
                      child: const Text('Отклонить'),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: ElevatedButton(
                      onPressed: onAccept,
                      style: ElevatedButton.styleFrom(
                        backgroundColor: MttColors.success,
                      ),
                      child: const Text('Принять'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTag(String text, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.1),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        text,
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w600,
          color: color,
        ),
      ),
    );
  }
}
```

### Priority Badge

```dart
// lib/features/work_orders/widgets/priority_badge.dart

import 'package:flutter/material.dart';
import '../models/work_order.dart';
import '../../../shared/constants/colors.dart';

class PriorityBadge extends StatelessWidget {
  const PriorityBadge({
    super.key,
    required this.priority,
    this.showLabel = false,
  });

  final WorkOrderPriority priority;
  final bool showLabel;

  @override
  Widget build(BuildContext context) {
    final color = MttColors.getPriorityColor(priority);
    final label = _getLabel();

    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: showLabel ? 8 : 6,
        vertical: 4,
      ),
      decoration: BoxDecoration(
        color: color,
        borderRadius: BorderRadius.circular(4),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            _getIcon(),
            size: 14,
            color: Colors.white,
          ),
          if (showLabel) ...[
            const SizedBox(width: 4),
            Text(
              label,
              style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.bold,
                color: Colors.white,
              ),
            ),
          ],
        ],
      ),
    );
  }

  IconData _getIcon() {
    switch (priority) {
      case WorkOrderPriority.low:
        return Icons.arrow_downward;
      case WorkOrderPriority.normal:
        return Icons.remove;
      case WorkOrderPriority.high:
        return Icons.arrow_upward;
      case WorkOrderPriority.urgent:
        return Icons.priority_high;
    }
  }

  String _getLabel() {
    switch (priority) {
      case WorkOrderPriority.low:
        return 'НИЗКИЙ';
      case WorkOrderPriority.normal:
        return 'ОБЫЧНЫЙ';
      case WorkOrderPriority.high:
        return 'ВЫСОКИЙ';
      case WorkOrderPriority.urgent:
        return 'СРОЧНО';
    }
  }
}
```

### Countdown Timer

```dart
// lib/features/work_orders/widgets/countdown_timer.dart

import 'dart:async';
import 'package:flutter/material.dart';
import '../../../shared/constants/colors.dart';

class CountdownTimer extends StatefulWidget {
  const CountdownTimer({
    super.key,
    required this.deadline,
  });

  final DateTime deadline;

  @override
  State<CountdownTimer> createState() => _CountdownTimerState();
}

class _CountdownTimerState extends State<CountdownTimer> {
  late Timer _timer;
  late Duration _remaining;

  @override
  void initState() {
    super.initState();
    _updateRemaining();
    _timer = Timer.periodic(
      const Duration(seconds: 1),
      (_) => _updateRemaining(),
    );
  }

  @override
  void dispose() {
    _timer.cancel();
    super.dispose();
  }

  void _updateRemaining() {
    setState(() {
      _remaining = widget.deadline.difference(DateTime.now());
    });
  }

  @override
  Widget build(BuildContext context) {
    final isOverdue = _remaining.isNegative;
    final isWarning = !isOverdue && _remaining.inMinutes < 10;

    final color = isOverdue
        ? MttColors.error
        : isWarning
            ? MttColors.warning
            : MttColors.textSecondary;

    final text = isOverdue
        ? 'Просрочено'
        : _formatDuration(_remaining);

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Icon(
          Icons.timer_outlined,
          size: 16,
          color: color,
        ),
        const SizedBox(width: 4),
        Text(
          text,
          style: TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w600,
            color: color,
          ),
        ),
      ],
    );
  }

  String _formatDuration(Duration duration) {
    final hours = duration.inHours;
    final minutes = duration.inMinutes.remainder(60);
    final seconds = duration.inSeconds.remainder(60);

    if (hours > 0) {
      return '${hours}ч ${minutes}м';
    } else if (minutes > 0) {
      return '${minutes}м ${seconds}с';
    } else {
      return '${seconds}с';
    }
  }
}
```

---

## 6. Placement Confirmation Widgets

### Container Info Card

```dart
// lib/features/placement/widgets/container_info_card.dart

import 'package:flutter/material.dart';
import '../../work_orders/models/work_order.dart';
import '../../../shared/constants/colors.dart';

class ContainerInfoCard extends StatelessWidget {
  const ContainerInfoCard({
    super.key,
    required this.workOrder,
  });

  final WorkOrder workOrder;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.inventory_2, color: MttColors.primary),
                const SizedBox(width: 8),
                Text(
                  workOrder.containerNumber,
                  style: const TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
            const Divider(height: 24),
            _buildInfoRow('Размер', workOrder.sizeDisplay),
            _buildInfoRow(
              'Статус',
              workOrder.statusDisplayRu,
              valueColor: workOrder.containerStatus == ContainerStatus.laden
                  ? MttColors.laden
                  : MttColors.empty,
            ),
            if (workOrder.weight != null)
              _buildInfoRow('Вес', '${workOrder.weight!.toStringAsFixed(0)} кг'),
            _buildInfoRow('Клиент', workOrder.customerName),
            if (workOrder.sealNumber != null)
              _buildInfoRow('Пломба', workOrder.sealNumber!),
            const Divider(height: 24),
            _buildInfoRow(
              'Позиция',
              workOrder.targetPosition.toCoordinate(),
              valueStyle: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.bold,
                color: MttColors.primary,
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(
    String label,
    String value, {
    Color? valueColor,
    TextStyle? valueStyle,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: const TextStyle(
              fontSize: 14,
              color: MttColors.textSecondary,
            ),
          ),
          Text(
            value,
            style: valueStyle ??
                TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                  color: valueColor ?? MttColors.textPrimary,
                ),
          ),
        ],
      ),
    );
  }
}
```

### Stacking Warning

```dart
// lib/features/placement/widgets/stacking_warning.dart

import 'package:flutter/material.dart';
import '../../../shared/constants/colors.dart';

class StackingWarning extends StatelessWidget {
  const StackingWarning({
    super.key,
    required this.containerBelow,
    required this.targetTier,
  });

  final String? containerBelow;
  final int targetTier;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: MttColors.warning.withOpacity(0.1),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: MttColors.warning),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.warning_amber_rounded,
                color: MttColors.warning,
              ),
              const SizedBox(width: 8),
              const Text(
                'Внимание: Штабелирование',
                style: TextStyle(
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  color: MttColors.warning,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            'Контейнер будет размещён на ярусе $targetTier.',
            style: const TextStyle(fontSize: 14),
          ),
          const SizedBox(height: 8),
          if (containerBelow != null) ...[
            const Text(
              'Контейнер снизу:',
              style: TextStyle(
                fontSize: 13,
                color: MttColors.textSecondary,
              ),
            ),
            const SizedBox(height: 4),
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: 12,
                vertical: 8,
              ),
              decoration: BoxDecoration(
                color: MttColors.containerFilled.withOpacity(0.1),
                borderRadius: BorderRadius.circular(4),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.inventory_2, size: 18),
                  const SizedBox(width: 8),
                  Text(
                    containerBelow!,
                    style: const TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      fontFamily: 'monospace',
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            const Text(
              'Убедитесь, что этот контейнер виден перед размещением.',
              style: TextStyle(
                fontSize: 13,
                fontStyle: FontStyle.italic,
                color: MttColors.textSecondary,
              ),
            ),
          ],
        ],
      ),
    );
  }
}
```

### Confirmation Screen

```dart
// lib/features/placement/screens/confirm_placement_screen.dart

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:camera/camera.dart';
import '../../work_orders/models/work_order.dart';
import '../providers/placement_provider.dart';
import '../../../shared/constants/colors.dart';
import '../../../shared/constants/dimensions.dart';

class ConfirmPlacementScreen extends ConsumerStatefulWidget {
  const ConfirmPlacementScreen({
    super.key,
    required this.workOrder,
  });

  final WorkOrder workOrder;

  @override
  ConsumerState<ConfirmPlacementScreen> createState() =>
      _ConfirmPlacementScreenState();
}

class _ConfirmPlacementScreenState
    extends ConsumerState<ConfirmPlacementScreen> {
  CameraController? _cameraController;
  XFile? _capturedPhoto;
  bool _isPlacedCorrectly = false;
  bool _isAligned = false;
  bool _hasIssue = false;
  final _notesController = TextEditingController();
  bool _isSubmitting = false;

  @override
  void initState() {
    super.initState();
    _initCamera();
  }

  Future<void> _initCamera() async {
    final cameras = await availableCameras();
    if (cameras.isNotEmpty) {
      _cameraController = CameraController(
        cameras.first,
        ResolutionPreset.medium,
      );
      await _cameraController!.initialize();
      if (mounted) setState(() {});
    }
  }

  @override
  void dispose() {
    _cameraController?.dispose();
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _takePhoto() async {
    if (_cameraController == null || !_cameraController!.value.isInitialized) {
      return;
    }

    try {
      final photo = await _cameraController!.takePicture();
      setState(() {
        _capturedPhoto = photo;
      });
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Ошибка камеры: $e')),
      );
    }
  }

  Future<void> _submitConfirmation() async {
    if (!_isPlacedCorrectly || !_isAligned) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Пожалуйста, подтвердите правильность размещения'),
          backgroundColor: MttColors.warning,
        ),
      );
      return;
    }

    setState(() => _isSubmitting = true);

    try {
      await ref.read(placementProvider.notifier).completePlacement(
        workOrderId: widget.workOrder.id,
        photoPath: _capturedPhoto?.path,
        notes: _notesController.text,
        hasIssue: _hasIssue,
      );

      if (mounted) {
        Navigator.of(context).popUntil((route) => route.isFirst);
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Размещение подтверждено'),
            backgroundColor: MttColors.success,
          ),
        );
      }
    } catch (e) {
      setState(() => _isSubmitting = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Ошибка: $e'),
          backgroundColor: MttColors.error,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Подтверждение'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(MttDimensions.screenPadding),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Container and position info
            _buildHeader(),
            const SizedBox(height: 24),

            // Camera / Photo
            _buildPhotoSection(),
            const SizedBox(height: 24),

            // Checklist
            _buildChecklist(),
            const SizedBox(height: 24),

            // Notes
            _buildNotesSection(),
            const SizedBox(height: 32),

            // Submit button
            _buildSubmitButton(),
            const SizedBox(height: 16),

            // Report issue button
            _buildReportIssueButton(),
          ],
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            const Icon(Icons.inventory_2, size: 32, color: MttColors.primary),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    widget.workOrder.containerNumber,
                    style: const TextStyle(
                      fontSize: 18,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      const Icon(Icons.location_on, size: 16, color: MttColors.primary),
                      const SizedBox(width: 4),
                      Text(
                        widget.workOrder.targetPosition.toCoordinate(),
                        style: const TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                          color: MttColors.primary,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPhotoSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Фото размещения (опционально)',
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 12),
        Container(
          height: 200,
          width: double.infinity,
          decoration: BoxDecoration(
            color: MttColors.surfaceVariant,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: MttColors.tierLine),
          ),
          child: _capturedPhoto != null
              ? Stack(
                  fit: StackFit.expand,
                  children: [
                    ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: Image.file(
                        File(_capturedPhoto!.path),
                        fit: BoxFit.cover,
                      ),
                    ),
                    Positioned(
                      top: 8,
                      right: 8,
                      child: IconButton(
                        icon: const Icon(Icons.close, color: Colors.white),
                        style: IconButton.styleFrom(
                          backgroundColor: Colors.black54,
                        ),
                        onPressed: () {
                          setState(() => _capturedPhoto = null);
                        },
                      ),
                    ),
                  ],
                )
              : _cameraController?.value.isInitialized == true
                  ? Stack(
                      fit: StackFit.expand,
                      children: [
                        ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: CameraPreview(_cameraController!),
                        ),
                        Positioned(
                          bottom: 16,
                          left: 0,
                          right: 0,
                          child: Center(
                            child: FloatingActionButton(
                              onPressed: _takePhoto,
                              backgroundColor: Colors.white,
                              child: const Icon(Icons.camera_alt, color: MttColors.primary),
                            ),
                          ),
                        ),
                      ],
                    )
                  : const Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(Icons.camera_alt, size: 48, color: MttColors.textSecondary),
                          SizedBox(height: 8),
                          Text(
                            'Камера недоступна',
                            style: TextStyle(color: MttColors.textSecondary),
                          ),
                        ],
                      ),
                    ),
        ),
      ],
    );
  }

  Widget _buildChecklist() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Проверка',
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 12),
        CheckboxListTile(
          value: _isPlacedCorrectly,
          onChanged: (v) => setState(() => _isPlacedCorrectly = v ?? false),
          title: const Text('Контейнер размещён правильно'),
          controlAffinity: ListTileControlAffinity.leading,
          contentPadding: EdgeInsets.zero,
        ),
        CheckboxListTile(
          value: _isAligned,
          onChanged: (v) => setState(() => _isAligned = v ?? false),
          title: const Text('Выровнен по разметке'),
          controlAffinity: ListTileControlAffinity.leading,
          contentPadding: EdgeInsets.zero,
        ),
        CheckboxListTile(
          value: _hasIssue,
          onChanged: (v) => setState(() => _hasIssue = v ?? false),
          title: const Text('Есть проблема (опишите ниже)'),
          controlAffinity: ListTileControlAffinity.leading,
          contentPadding: EdgeInsets.zero,
        ),
      ],
    );
  }

  Widget _buildNotesSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Примечания',
          style: TextStyle(
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _notesController,
          maxLines: 3,
          decoration: const InputDecoration(
            hintText: 'Введите примечания...',
            border: OutlineInputBorder(),
          ),
        ),
      ],
    );
  }

  Widget _buildSubmitButton() {
    return ElevatedButton.icon(
      onPressed: _isSubmitting ? null : _submitConfirmation,
      icon: _isSubmitting
          ? const SizedBox(
              width: 20,
              height: 20,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                color: Colors.white,
              ),
            )
          : const Icon(Icons.check),
      label: Text(_isSubmitting ? 'Отправка...' : 'ПОДТВЕРДИТЬ РАЗМЕЩЕНИЕ'),
      style: ElevatedButton.styleFrom(
        backgroundColor: MttColors.success,
        padding: const EdgeInsets.symmetric(vertical: 16),
      ),
    );
  }

  Widget _buildReportIssueButton() {
    return OutlinedButton.icon(
      onPressed: () {
        // TODO: Navigate to issue report screen
      },
      icon: const Icon(Icons.warning_amber_rounded),
      label: const Text('Сообщить о проблеме'),
      style: OutlinedButton.styleFrom(
        foregroundColor: MttColors.warning,
        side: const BorderSide(color: MttColors.warning),
        padding: const EdgeInsets.symmetric(vertical: 16),
      ),
    );
  }
}
```

---

## 7. State Management

### Riverpod Providers

```dart
// lib/features/placement/providers/placement_provider.dart

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../models/yard_layout.dart';
import '../services/placement_service.dart';

part 'placement_provider.g.dart';

@riverpod
PlacementService placementService(PlacementServiceRef ref) {
  return PlacementService(ref.watch(apiClientProvider));
}

@riverpod
Future<YardLayout> yardLayout(
  YardLayoutRef ref,
  String zone,
) async {
  final service = ref.watch(placementServiceProvider);
  return service.getLayout(zone);
}

@riverpod
class Placement extends _$Placement {
  @override
  AsyncValue<void> build() => const AsyncValue.data(null);

  Future<void> completePlacement({
    required String workOrderId,
    String? photoPath,
    String? notes,
    bool hasIssue = false,
  }) async {
    state = const AsyncValue.loading();

    try {
      final service = ref.read(placementServiceProvider);
      await service.completePlacement(
        workOrderId: workOrderId,
        photoPath: photoPath,
        notes: notes,
        hasIssue: hasIssue,
      );

      // Invalidate work orders to refresh list
      ref.invalidate(workOrdersProvider);

      state = const AsyncValue.data(null);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
      rethrow;
    }
  }
}
```

### Work Orders Provider

```dart
// lib/features/work_orders/providers/work_order_provider.dart

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import '../models/work_order.dart';
import '../services/work_order_service.dart';

part 'work_order_provider.g.dart';

@riverpod
WorkOrderService workOrderService(WorkOrderServiceRef ref) {
  return WorkOrderService(ref.watch(apiClientProvider));
}

@riverpod
Future<List<WorkOrder>> workOrders(WorkOrdersRef ref) async {
  final service = ref.watch(workOrderServiceProvider);
  return service.getMyOrders();
}

@riverpod
class WorkOrderActions extends _$WorkOrderActions {
  @override
  AsyncValue<void> build() => const AsyncValue.data(null);

  Future<void> accept(String workOrderId) async {
    state = const AsyncValue.loading();

    try {
      final service = ref.read(workOrderServiceProvider);
      await service.acceptOrder(workOrderId);
      ref.invalidate(workOrdersProvider);
      state = const AsyncValue.data(null);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
      rethrow;
    }
  }

  Future<void> decline(String workOrderId, String reason) async {
    state = const AsyncValue.loading();

    try {
      final service = ref.read(workOrderServiceProvider);
      await service.declineOrder(workOrderId, reason);
      ref.invalidate(workOrdersProvider);
      state = const AsyncValue.data(null);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
      rethrow;
    }
  }

  Future<void> start(String workOrderId) async {
    state = const AsyncValue.loading();

    try {
      final service = ref.read(workOrderServiceProvider);
      await service.startPlacement(workOrderId);
      ref.invalidate(workOrdersProvider);
      state = const AsyncValue.data(null);
    } catch (e, st) {
      state = AsyncValue.error(e, st);
      rethrow;
    }
  }
}
```

---

## 8. Offline Support

### Offline Queue

```dart
// lib/core/sync/offline_queue.dart

import 'package:hive/hive.dart';
import 'package:uuid/uuid.dart';

enum QueueActionType {
  acceptOrder,
  declineOrder,
  startPlacement,
  completePlacement,
}

class QueuedAction {
  final String id;
  final QueueActionType type;
  final Map<String, dynamic> payload;
  final DateTime createdAt;
  int retryCount;

  QueuedAction({
    required this.id,
    required this.type,
    required this.payload,
    required this.createdAt,
    this.retryCount = 0,
  });

  Map<String, dynamic> toJson() => {
    'id': id,
    'type': type.name,
    'payload': payload,
    'createdAt': createdAt.toIso8601String(),
    'retryCount': retryCount,
  };

  factory QueuedAction.fromJson(Map<String, dynamic> json) => QueuedAction(
    id: json['id'],
    type: QueueActionType.values.byName(json['type']),
    payload: Map<String, dynamic>.from(json['payload']),
    createdAt: DateTime.parse(json['createdAt']),
    retryCount: json['retryCount'] ?? 0,
  );
}

class OfflineQueue {
  static const _boxName = 'offline_queue';
  late Box<Map> _box;

  Future<void> init() async {
    _box = await Hive.openBox<Map>(_boxName);
  }

  Future<void> enqueue(QueueActionType type, Map<String, dynamic> payload) async {
    final action = QueuedAction(
      id: const Uuid().v4(),
      type: type,
      payload: payload,
      createdAt: DateTime.now(),
    );
    await _box.put(action.id, action.toJson());
  }

  List<QueuedAction> getAll() {
    return _box.values
        .map((v) => QueuedAction.fromJson(Map<String, dynamic>.from(v)))
        .toList()
      ..sort((a, b) => a.createdAt.compareTo(b.createdAt));
  }

  Future<void> remove(String actionId) async {
    await _box.delete(actionId);
  }

  Future<void> incrementRetry(String actionId) async {
    final action = _box.get(actionId);
    if (action != null) {
      action['retryCount'] = (action['retryCount'] ?? 0) + 1;
      await _box.put(actionId, action);
    }
  }

  int get pendingCount => _box.length;

  bool get hasPending => _box.isNotEmpty;
}
```

### Sync Service

```dart
// lib/core/sync/sync_service.dart

import 'dart:async';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'offline_queue.dart';
import '../api/api_client.dart';

class SyncService {
  final OfflineQueue _queue;
  final ApiClient _apiClient;
  final Ref _ref;

  StreamSubscription? _connectivitySubscription;
  Timer? _syncTimer;
  bool _isSyncing = false;

  SyncService(this._queue, this._apiClient, this._ref);

  void start() {
    // Listen for connectivity changes
    _connectivitySubscription = Connectivity()
        .onConnectivityChanged
        .listen((result) {
      if (result != ConnectivityResult.none) {
        _syncPending();
      }
    });

    // Periodic sync every 30 seconds
    _syncTimer = Timer.periodic(
      const Duration(seconds: 30),
      (_) => _syncPending(),
    );
  }

  void stop() {
    _connectivitySubscription?.cancel();
    _syncTimer?.cancel();
  }

  Future<void> _syncPending() async {
    if (_isSyncing || !_queue.hasPending) return;

    _isSyncing = true;
    final actions = _queue.getAll();

    for (final action in actions) {
      if (action.retryCount >= 5) {
        // Max retries exceeded, remove from queue
        await _queue.remove(action.id);
        continue;
      }

      try {
        await _processAction(action);
        await _queue.remove(action.id);
      } catch (e) {
        await _queue.incrementRetry(action.id);
        // Exponential backoff: wait before next retry
        await Future.delayed(
          Duration(seconds: (2 << action.retryCount).clamp(1, 60)),
        );
      }
    }

    _isSyncing = false;
  }

  Future<void> _processAction(QueuedAction action) async {
    switch (action.type) {
      case QueueActionType.acceptOrder:
        await _apiClient.post(
          '/api/terminal/work-orders/${action.payload['id']}/accept/',
        );
        break;
      case QueueActionType.declineOrder:
        await _apiClient.post(
          '/api/terminal/work-orders/${action.payload['id']}/decline/',
          data: {'reason': action.payload['reason']},
        );
        break;
      case QueueActionType.startPlacement:
        await _apiClient.post(
          '/api/terminal/work-orders/${action.payload['id']}/start/',
        );
        break;
      case QueueActionType.completePlacement:
        // Handle photo upload if present
        await _apiClient.post(
          '/api/terminal/work-orders/${action.payload['id']}/complete/',
          data: action.payload,
        );
        break;
    }
  }
}
```

---

## 9. API Integration

### API Client

```dart
// lib/core/api/api_client.dart

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../database/hive_service.dart';

final apiClientProvider = Provider<ApiClient>((ref) {
  return ApiClient(
    baseUrl: 'https://api.mtt-terminal.com',
    hiveService: ref.watch(hiveServiceProvider),
  );
});

class ApiClient {
  final Dio _dio;
  final HiveService _hiveService;

  ApiClient({
    required String baseUrl,
    required HiveService hiveService,
  })  : _hiveService = hiveService,
        _dio = Dio(BaseOptions(
          baseUrl: baseUrl,
          connectTimeout: const Duration(seconds: 10),
          receiveTimeout: const Duration(seconds: 10),
        )) {
    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await _hiveService.getAccessToken();
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        return handler.next(options);
      },
      onError: (error, handler) async {
        if (error.response?.statusCode == 401) {
          // Try to refresh token
          final refreshed = await _refreshToken();
          if (refreshed) {
            // Retry original request
            final response = await _dio.fetch(error.requestOptions);
            return handler.resolve(response);
          }
        }
        return handler.next(error);
      },
    ));
  }

  Future<bool> _refreshToken() async {
    try {
      final refreshToken = await _hiveService.getRefreshToken();
      if (refreshToken == null) return false;

      final response = await _dio.post(
        '/api/auth/token/refresh/',
        data: {'refresh': refreshToken},
      );

      final newAccessToken = response.data['access'];
      await _hiveService.saveAccessToken(newAccessToken);
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<Response<T>> get<T>(
    String path, {
    Map<String, dynamic>? queryParameters,
  }) {
    return _dio.get<T>(path, queryParameters: queryParameters);
  }

  Future<Response<T>> post<T>(
    String path, {
    dynamic data,
  }) {
    return _dio.post<T>(path, data: data);
  }

  Future<Response<T>> patch<T>(
    String path, {
    dynamic data,
  }) {
    return _dio.patch<T>(path, data: data);
  }

  Future<Response<T>> delete<T>(String path) {
    return _dio.delete<T>(path);
  }
}
```

---

## Summary

This Flutter widget design provides:

1. **2D Visualization System**
   - Top-down grid view with tier counts
   - Side view for stacking visualization
   - Color-coded cells for quick understanding
   - Target position highlighting

2. **Work Order Management**
   - Prioritized order cards
   - Real-time countdown timers
   - Accept/Decline workflow

3. **Placement Confirmation**
   - Photo capture integration
   - Checklist verification
   - Notes and issue reporting

4. **Offline Support**
   - Hive for fast local storage
   - Action queue with retry logic
   - Automatic sync on connectivity

5. **State Management**
   - Riverpod for clean architecture
   - Provider-based dependency injection
   - Async value handling

The design prioritizes:
- **Glanceability** - Quick understanding while moving
- **Reliability** - Offline-first architecture
- **Simplicity** - Clear, focused UI for yard operations
- **Performance** - Native rendering, no WebView

---

*Document Version: 1.0*
*Framework: Flutter 3.10+*
*State Management: Riverpod 2.x*
