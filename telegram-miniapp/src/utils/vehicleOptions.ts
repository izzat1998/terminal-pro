/**
 * Vehicle option tree builders for CascaderView
 * Builds hierarchical selection trees for vehicle types, transport modes, and cargo
 */

import type { CascaderOption } from 'antd-mobile/es/components/cascader-view';
import type { ChoiceOption, ChoicesResponse } from '@/types/api';

/**
 * Build container type options with destinations
 */
export const buildContainerTypeOptions = (
  destinationOptions: CascaderOption[],
  containerSizes: ChoiceOption[],
  loadStatuses: ChoiceOption[]
): CascaderOption[] => {
  return containerSizes.map(size => ({
    label: size.label,
    value: size.value.toLowerCase(),
    children: loadStatuses.map(status => ({
      label: status.label,
      value: status.value.toLowerCase(),
      children: destinationOptions,
    })),
  }));
};

/**
 * Build cargo type options for container-capable vehicles
 */
export const buildCargoTypeOptionsWithContainer = (
  destinationOptions: CascaderOption[],
  cargoTypes: ChoiceOption[],
  containerSizes: ChoiceOption[],
  loadStatuses: ChoiceOption[]
): CascaderOption[] => {
  return cargoTypes.map(cargo => {
    if (cargo.value === 'CONTAINER') {
      return {
        label: cargo.label,
        value: cargo.value.toLowerCase(),
        children: buildContainerTypeOptions(destinationOptions, containerSizes, loadStatuses),
      };
    }
    return {
      label: cargo.label,
      value: cargo.value.toLowerCase(),
      children: destinationOptions,
    };
  });
};

/**
 * Build cargo type options for non-container vehicles
 */
export const buildCargoTypeOptionsWithoutContainer = (
  destinationOptions: CascaderOption[],
  cargoTypes: ChoiceOption[]
): CascaderOption[] => {
  return cargoTypes
    .filter(cargo => cargo.value !== 'CONTAINER')
    .map(cargo => ({
      label: cargo.label,
      value: cargo.value.toLowerCase(),
      children: destinationOptions,
    }));
};

/**
 * Build cargo vehicle options with load status
 */
export const buildCargoVehicleOptions = (
  destinationOptions: CascaderOption[],
  transportTypes: ChoiceOption[],
  loadStatuses: ChoiceOption[],
  cargoTypes: ChoiceOption[],
  containerSizes: ChoiceOption[]
): CascaderOption[] => {
  // Container-capable vehicles
  const containerCapable = ['PLATFORM', 'TRUCK', 'TRAILER'];

  return transportTypes.map(transport => {
    const canCarryContainer = containerCapable.includes(transport.value);

    return {
      label: transport.label,
      value: transport.value.toLowerCase(),
      children: loadStatuses.map(status => {
        if (status.value === 'LOADED') {
          return {
            label: status.label,
            value: status.value.toLowerCase(),
            children: canCarryContainer
              ? buildCargoTypeOptionsWithContainer(destinationOptions, cargoTypes, containerSizes, loadStatuses)
              : buildCargoTypeOptionsWithoutContainer(destinationOptions, cargoTypes),
          };
        }
        return {
          label: status.label,
          value: status.value.toLowerCase(),
          children: destinationOptions,
        };
      }),
    };
  });
};

/**
 * Build main vehicle type options tree
 */
export const buildVehicleTypeOptions = (
  destinationOptions: CascaderOption[],
  choices: ChoicesResponse
): CascaderOption[] => {
  return choices.vehicle_types.map(vehicleType => {
    if (vehicleType.value === 'LIGHT') {
      return {
        label: vehicleType.label,
        value: vehicleType.value.toLowerCase(),
        children: choices.visitor_types.map(visitor => ({
          label: visitor.label,
          value: visitor.value.toLowerCase(),
        })),
      };
    }
    // CARGO vehicle
    return {
      label: vehicleType.label,
      value: vehicleType.value.toLowerCase(),
      children: buildCargoVehicleOptions(
        destinationOptions,
        choices.transport_types,
        choices.load_statuses,
        choices.cargo_types,
        choices.container_sizes
      ),
    };
  });
};
