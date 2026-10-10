//+------------------------------------------------------------------+
//| Windows AI Trading Agent - chart-only companion                  |
//| NO trading functions, no arbitrary scripts or file names.       |
//| Install one copy on an open MT5 chart and allow a 1-second timer.|
//+------------------------------------------------------------------+
#property strict
#property version "0.10"

#define REQUEST_FILE  "agent_request.txt"
#define RESPONSE_FILE "agent_response.txt"

bool ValidIdentifier(const string id)
  {
   if(StringLen(id)!=32) return false;
   for(int i=0;i<32;i++)
     {
      int c=StringGetCharacter(id,i);
      if(!((c>='0' && c<='9') || (c>='a' && c<='f'))) return false;
     }
   return true;
  }

bool ValidSymbol(const string symbol)
  {
   if(StringLen(symbol)<1 || StringLen(symbol)>32) return false;
   for(int i=0;i<StringLen(symbol);i++)
     {
      int c=StringGetCharacter(symbol,i);
      if(!((c>='A' && c<='Z') || (c>='a' && c<='z') ||
           (c>='0' && c<='9') || c=='.' || c=='_' || c=='-')) return false;
     }
   return true;
  }

ENUM_TIMEFRAMES DecodeTimeframe(const string value)
  {
   if(value=="M1") return PERIOD_M1;
   if(value=="M5") return PERIOD_M5;
   if(value=="M15") return PERIOD_M15;
   if(value=="M30") return PERIOD_M30;
   if(value=="H1") return PERIOD_H1;
   if(value=="H4") return PERIOD_H4;
   if(value=="D1") return PERIOD_D1;
   return PERIOD_CURRENT;
  }

void Reply(const string id,const string status,const long chart,const string explanation)
  {
   int handle=FileOpen(RESPONSE_FILE,FILE_COMMON|FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(handle==INVALID_HANDLE)
     {
      Print("ChartControlEA cannot write response: ",GetLastError());
      return;
     }
   FileWriteString(handle,id+"|"+status+"|"+IntegerToString(chart)+"|"+explanation);
   FileFlush(handle);
   FileClose(handle);
  }

int OnInit()
  {
   EventSetTimer(1);
   Print("ChartControlEA online (chart operations only, trading disabled)");
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
  }

void OnTimer()
  {
   if(!FileIsExist(REQUEST_FILE,FILE_COMMON)) return;
   int file=FileOpen(REQUEST_FILE,FILE_COMMON|FILE_READ|FILE_TXT|FILE_ANSI);
   if(file==INVALID_HANDLE) return;
   string request=FileReadString(file);
   FileClose(file);
   // Claim before acting; a terminal restart must not replay the request.
   if(!FileDelete(REQUEST_FILE,FILE_COMMON)) return;

   string fields[];
   int count=StringSplit(request,'|',fields);
   if(count!=6) return; // Never execute malformed requests.
   string id=fields[0];
   if(!ValidIdentifier(id)) return;
   long expiry=(long)StringToInteger(fields[1]);
   long now=(long)TimeLocal();
   if(expiry<now || expiry>now+16)
     {
      Reply(id,"ERROR",0,"expired_or_invalid_expiry");
      return;
     }
   string action=fields[2];
   string symbol=fields[3];
   ENUM_TIMEFRAMES timeframe=DecodeTimeframe(fields[4]);
   int ma_period=(int)StringToInteger(fields[5]);
   if(!ValidSymbol(symbol) || timeframe==PERIOD_CURRENT || ma_period<2 || ma_period>500 ||
      (action!="OPEN" && action!="SMA" && action!="EMA"))
     {
      Reply(id,"ERROR",0,"invalid_or_unsupported_parameters");
      return;
     }
   if(!SymbolSelect(symbol,true))
     {
      Reply(id,"ERROR",0,"symbol_not_available");
      return;
     }
   long chart=ChartOpen(symbol,timeframe);
   if(chart<=0)
     {
      Reply(id,"ERROR",0,"chart_open_failed");
      return;
     }
   ChartRedraw(chart);
   if(ChartSymbol(chart)!=symbol || ChartPeriod(chart)!=timeframe)
     {
      Reply(id,"ERROR",chart,"chart_state_not_verified");
      return;
     }
   if(action=="OPEN")
     {
      Reply(id,"OK",chart,"chart_symbol_and_timeframe_verified");
      return;
     }
   ENUM_MA_METHOD method=(action=="EMA") ? MODE_EMA : MODE_SMA;
   int handle=iMA(symbol,timeframe,ma_period,0,method,PRICE_CLOSE);
   if(handle==INVALID_HANDLE)
     {
      Reply(id,"ERROR",chart,"indicator_handle_invalid");
      return;
     }
   int before=ChartIndicatorsTotal(chart,0);
   if(!ChartIndicatorAdd(chart,0,handle))
     {
      IndicatorRelease(handle);
      Reply(id,"ERROR",chart,"chart_indicator_add_failed");
      return;
     }
   ChartRedraw(chart);
   int after=ChartIndicatorsTotal(chart,0);
   if(after<=before)
     {
      Reply(id,"ERROR",chart,"indicator_count_not_verified");
      return;
     }
   Reply(id,"OK",chart,"moving_average_added_and_indicator_count_increased");
  }
