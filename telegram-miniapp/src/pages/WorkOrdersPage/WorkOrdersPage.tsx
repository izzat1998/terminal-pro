import type { FC } from 'react';
import { useEffect, useState, useCallback } from 'react';
import { Page } from '@/components/Page';
import {
  Card,
  Button,
  DotLoading,
  Toast,
  PullToRefresh,
  Empty,
  Dialog,
  FloatingBubble,
  Badge,
} from 'antd-mobile';
import { Package, Clock, AlertCircle, CheckCircle, ClipboardList } from 'lucide-react';
import { initData, useSignal } from '@tma.js/sdk-react';
import { API_ENDPOINTS, getPriorityColor } from '@/config/api';
import { YardMap } from '@/components/YardMap';
import { WorkOrderTaskPopup } from '@/components/WorkOrderTaskPopup';
import type { WorkOrder, WorkOrdersResponse } from '@/types/api';

export const WorkOrdersPage: FC = () => {
  const [orders, setOrders] = useState<WorkOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [completing, setCompleting] = useState<number | null>(null);
  const [showQuickView, setShowQuickView] = useState(false);

  // Get Telegram user ID for API authentication
  const initDataState = useSignal(initData.state);
  const telegramUserId = initDataState?.user?.id;

  const fetchOrders = useCallback(async () => {
    try {
      setLoading(true);
      // In dev mode without Telegram, skip telegram_id (backend will use fallback)
      const url = telegramUserId
        ? `${API_ENDPOINTS.workOrders.myOrders}?telegram_id=${telegramUserId}`
        : API_ENDPOINTS.workOrders.myOrders;
      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to fetch');
      const data: WorkOrdersResponse = await response.json();
      // Filter to only show active orders (not completed/verified/failed)
      const activeOrders = data.results.filter(
        (order) => !['COMPLETED', 'VERIFIED', 'FAILED'].includes(order.status)
      );
      setOrders(activeOrders);
    } catch {
      Toast.show({ icon: 'fail', content: 'Юклашда хатолик' });
    } finally {
      setLoading(false);
    }
  }, [telegramUserId]);

  useEffect(() => {
    void fetchOrders();
  }, [fetchOrders]);

  const handleComplete = async (order: WorkOrder) => {
    const result = await Dialog.confirm({
      content: (
        <div className="text-center">
          <div className="text-lg font-medium mb-2">Тасдиқлаш</div>
          <div className="text-gray-600">
            <span className="font-medium">{order.container_number}</span> контейнери
            <span className="font-medium"> {order.target_coordinate}</span> жойга қўйилдими?
          </div>
        </div>
      ),
      confirmText: 'Ҳа, бажарилди',
      cancelText: 'Йўқ',
    });

    if (!result) return;

    try {
      setCompleting(order.id);
      // In dev mode without Telegram, skip telegram_id
      const url = telegramUserId
        ? `${API_ENDPOINTS.workOrders.complete(order.id)}?telegram_id=${telegramUserId}`
        : API_ENDPOINTS.workOrders.complete(order.id);
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error?.message || 'Failed to complete');
      }

      Toast.show({
        icon: 'success',
        content: 'Бажарилди',
      });

      // Remove from list
      setOrders((prev) => prev.filter((o) => o.id !== order.id));
    } catch (err) {
      Toast.show({
        icon: 'fail',
        content: err instanceof Error ? err.message : 'Хатолик юз берди',
      });
    } finally {
      setCompleting(null);
    }
  };

  const formatDeadline = (deadline: string | null, isOverdue: boolean) => {
    if (!deadline) return null;

    const deadlineDate = new Date(deadline);
    const now = new Date();
    const diffMs = deadlineDate.getTime() - now.getTime();
    const diffMins = Math.floor(diffMs / 60000);

    if (isOverdue) {
      return (
        <span className="text-red-500 font-medium flex items-center gap-1">
          <AlertCircle size={14} />
          Муддати ўтган
        </span>
      );
    }

    if (diffMins < 60) {
      return (
        <span className="text-orange-500 font-medium">
          {diffMins} дақиқа қолди
        </span>
      );
    }

    const hours = Math.floor(diffMins / 60);
    const mins = diffMins % 60;
    return (
      <span className="text-gray-600">
        {hours} соат {mins > 0 ? `${mins} дақ` : ''} қолди
      </span>
    );
  };

  const getPriorityIcon = (priority: string) => {
    const size = 8;
    const color = getPriorityColor(priority);
    return (
      <span
        className="inline-block rounded-full"
        style={{
          width: size,
          height: size,
          backgroundColor: color,
          boxShadow: priority === 'URGENT' ? `0 0 6px ${color}` : 'none',
        }}
      />
    );
  };

  return (
    <Page back={false} title="Вазифалар">
      <PullToRefresh onRefresh={fetchOrders}>
        <div className="p-3 pb-24 min-h-screen">
          {loading && (
            <div className="flex flex-col items-center justify-center py-20">
              <DotLoading color="primary" />
              <div className="mt-3 text-gray-500">Юкланмоқда...</div>
            </div>
          )}

          {!loading && orders.length === 0 && (
            <Empty
              style={{ padding: '64px 0' }}
              imageStyle={{ width: 128 }}
              description={
                <div className="text-gray-500">
                  <div className="text-lg font-medium mb-1">Вазифалар йўқ</div>
                  <div className="text-sm">Ҳозирча сизга тайинланган вазифалар йўқ</div>
                </div>
              }
            />
          )}

          {!loading && orders.length > 0 && (
            <div className="space-y-3">
              {orders.map((order) => (
                <Card
                  key={order.id}
                  className="overflow-hidden"
                  style={{
                    borderRadius: '12px',
                    border: order.is_overdue ? '2px solid #ff3141' : '1px solid #f0f0f0',
                  }}
                >
                  {/* Header with priority and order number */}
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      {getPriorityIcon(order.priority)}
                      <span className="text-xs text-gray-400 font-mono">
                        #{order.order_number}
                      </span>
                    </div>
                    <div className="flex items-center gap-1 text-xs">
                      <Clock size={12} className="text-gray-400" />
                      {formatDeadline(order.sla_deadline, order.is_overdue)}
                    </div>
                  </div>

                  {/* Container info */}
                  <div className="flex items-start gap-3 mb-3">
                    <div
                      className="flex items-center justify-center rounded-lg p-2"
                      style={{ backgroundColor: '#f5f5f5' }}
                    >
                      <Package size={24} className="text-blue-600" />
                    </div>
                    <div className="flex-1">
                      <div className="font-semibold text-lg tracking-wide">
                        {order.container_number}
                      </div>
                      <div className="text-sm text-gray-500">
                        {order.container_size}
                      </div>
                    </div>
                  </div>

                  {/* Target location - 2D Map */}
                  <div className="mb-3">
                    <YardMap
                      targetCoordinate={order.target_coordinate}
                      containerSize={order.container_size}
                      containerNumber={order.container_number}
                    />
                  </div>

                  {/* Complete button */}
                  <Button
                    block
                    color="primary"
                    size="large"
                    loading={completing === order.id}
                    disabled={completing !== null}
                    onClick={() => handleComplete(order)}
                    style={{
                      borderRadius: '10px',
                      height: '48px',
                      fontSize: '16px',
                      fontWeight: 600,
                    }}
                  >
                    <div className="flex items-center justify-center gap-2">
                      <CheckCircle size={20} />
                      Бажарилди
                    </div>
                  </Button>
                </Card>
              ))}
            </div>
          )}
        </div>
      </PullToRefresh>

      {/* Quick View FAB */}
      <FloatingBubble
        style={{
          '--initial-position-bottom': '84px',
          '--initial-position-right': '16px',
          '--edge-distance': '16px',
          '--size': '56px',
          '--background': '#1677ff',
        }}
        onClick={() => setShowQuickView(true)}
      >
        <Badge
          content={orders.length > 0 ? orders.length : null}
          style={{
            '--color': '#ff8f1f',
            '--top': '-4px',
            '--right': '-4px',
          }}
        >
          <ClipboardList size={24} color="white" />
        </Badge>
      </FloatingBubble>

      {/* Quick View Popup */}
      <WorkOrderTaskPopup
        visible={showQuickView}
        onClose={() => setShowQuickView(false)}
        orders={orders}
        loading={loading}
      />
    </Page>
  );
};
