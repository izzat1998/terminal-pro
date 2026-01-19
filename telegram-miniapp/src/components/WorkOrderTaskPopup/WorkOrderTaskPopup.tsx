import type { FC } from 'react';
import { useState } from 'react';
import { Popup, Card, DotLoading, Empty, Badge, Tag } from 'antd-mobile';
import { Package, Clock, MapPin, ChevronDown, ChevronUp } from 'lucide-react';
import { getPriorityColor } from '@/config/api';
import { YardMap } from '@/components/YardMap';
import type { WorkOrder } from '@/types/api';

interface WorkOrderTaskPopupProps {
  visible: boolean;
  onClose: () => void;
  orders: WorkOrder[];
  loading: boolean;
}

export const WorkOrderTaskPopup: FC<WorkOrderTaskPopupProps> = ({
  visible,
  onClose,
  orders,
  loading,
}) => {
  const [expandedOrderId, setExpandedOrderId] = useState<number | null>(null);

  const toggleExpand = (orderId: number) => {
    setExpandedOrderId((prev) => (prev === orderId ? null : orderId));
  };

  const formatDeadline = (deadline: string | null, isOverdue: boolean) => {
    if (!deadline) return null;

    const deadlineDate = new Date(deadline);
    const now = new Date();
    const diffMs = deadlineDate.getTime() - now.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (isOverdue) {
      return <span className="text-red-500 font-medium">Муддати ўтган</span>;
    }

    if (diffMins < 60) {
      return <span className="text-orange-500">{diffMins} дақиқа қолди</span>;
    }

    const hours = Math.floor(diffMins / 60);
    const mins = diffMins % 60;
    return (
      <span className="text-gray-600">
        {hours} соат {mins > 0 ? `${mins} дақ` : ''} қолди
      </span>
    );
  };

  const getPriorityLabel = (priority: string) => {
    const labels: Record<string, string> = {
      LOW: 'Паст',
      MEDIUM: 'Ўрта',
      HIGH: 'Юқори',
      URGENT: 'Шошилинч',
    };
    return labels[priority] || priority;
  };

  return (
    <Popup
      visible={visible}
      onMaskClick={onClose}
      position="bottom"
      bodyStyle={{
        borderTopLeftRadius: 16,
        borderTopRightRadius: 16,
        maxHeight: '70vh',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <div className="flex items-center gap-2">
          <span className="text-lg font-semibold">Вазифалар</span>
          <Badge
            content={orders.length}
            style={{
              '--color': orders.length > 0 ? '#ff8f1f' : '#00b578',
            }}
          />
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
        >
          ×
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {loading && (
          <div className="flex flex-col items-center justify-center py-12">
            <DotLoading color="primary" />
            <div className="mt-3 text-gray-500">Юкланмоқда...</div>
          </div>
        )}

        {!loading && orders.length === 0 && (
          <Empty
            style={{ padding: '48px 0' }}
            description={
              <div className="text-gray-500 text-center">
                <div className="text-base font-medium mb-1">Вазифалар йўқ</div>
                <div className="text-sm">
                  Ҳозирча сизга тайинланган вазифалар йўқ
                </div>
              </div>
            }
          />
        )}

        {!loading &&
          orders.map((order) => {
            const isExpanded = expandedOrderId === order.id;
            return (
              <Card
                key={order.id}
                className="overflow-hidden"
                style={{
                  borderRadius: 12,
                  border: order.is_overdue
                    ? '2px solid #ff3141'
                    : '1px solid #f0f0f0',
                }}
              >
                {/* Task Header - Clickable to expand */}
                <div
                  className="cursor-pointer"
                  onClick={() => toggleExpand(order.id)}
                >
                  {/* Priority & Order Number */}
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span
                        className="inline-block w-2 h-2 rounded-full"
                        style={{ backgroundColor: getPriorityColor(order.priority) }}
                      />
                      <Tag
                        color="default"
                        style={{
                          '--border-color': getPriorityColor(order.priority),
                          '--text-color': getPriorityColor(order.priority),
                          '--background-color': 'transparent',
                          fontSize: 11,
                          padding: '0 6px',
                          borderRadius: 4,
                        }}
                      >
                        {getPriorityLabel(order.priority)}
                      </Tag>
                      <span className="text-xs text-gray-400 font-mono">
                        #{order.order_number}
                      </span>
                    </div>
                    <div className="flex items-center gap-1 text-xs">
                      <Clock size={12} className="text-gray-400" />
                      {formatDeadline(order.sla_deadline, order.is_overdue)}
                    </div>
                  </div>

                  {/* Container Info */}
                  <div className="flex items-center gap-3">
                    <div
                      className="flex items-center justify-center rounded-lg p-2"
                      style={{ backgroundColor: '#f5f5f5' }}
                    >
                      <Package size={20} className="text-blue-600" />
                    </div>
                    <div className="flex-1">
                      <div className="font-semibold text-base tracking-wide">
                        {order.container_number}
                      </div>
                      <div className="text-sm text-gray-500 flex items-center gap-2">
                        <span>{order.container_size}</span>
                        <span className="text-gray-300">•</span>
                        <MapPin size={12} className="text-gray-400" />
                        <span>{order.target_coordinate}</span>
                      </div>
                    </div>
                    <div className="text-gray-400">
                      {isExpanded ? (
                        <ChevronUp size={20} />
                      ) : (
                        <ChevronDown size={20} />
                      )}
                    </div>
                  </div>
                </div>

                {/* Expanded YardMap */}
                {isExpanded && (
                  <div className="mt-3 pt-3 border-t border-gray-100">
                    <YardMap
                      targetCoordinate={order.target_coordinate}
                      containerSize={order.container_size}
                      containerNumber={order.container_number}
                    />
                  </div>
                )}
              </Card>
            );
          })}
      </div>
    </Popup>
  );
};
