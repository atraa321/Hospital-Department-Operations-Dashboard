import ReactEChartsCore from 'echarts-for-react/lib/core';
import * as echarts from 'echarts/core';
import { BarChart, LineChart, PieChart } from 'echarts/charts';
import { GridComponent, LegendComponent, TitleComponent, TooltipComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';

echarts.use([BarChart, LineChart, PieChart, GridComponent, LegendComponent, TitleComponent, TooltipComponent, CanvasRenderer]);

interface EChartProps {
  option: object;
  style?: React.CSSProperties;
}

export function EChart({ option, style }: EChartProps) {
  return <ReactEChartsCore echarts={echarts} option={option} style={style} notMerge lazyUpdate />;
}
