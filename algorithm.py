import pandas as pd
from glob import glob
import glob2
import os
import numpy as np
import plotly.express as px
import pydeck as pdk
import geopandas as gpd

# Define a simple colormap with key RGBA values (Plasma-like colors)
plasma_colormap = [
    [12, 7, 134, 255],   # Dark blue (start)
    [219, 91, 103, 255],  # Pink
    [239, 248, 33, 255], # Yellow (end)
]

def algorithm(outlined_buildings=[], dropdownValue='By Demand', battery_efficiency=1, buildings_update=[]):
    if not outlined_buildings:
        return create_figures()

    csvfiles_final = glob2.glob(os.path.join('./viana_do_castelo', 'B*[0-9]_final.csv')) # paths for the building files

    dataframes_final = [] #empty list
    for csvfile_final in csvfiles_final:
        df_final = pd.read_csv(csvfile_final, sep =',') #opening the file
        df_final= df_final.rename(columns={'Unnamed: 0': 'Date'})# rename 1st columns
        dataframes_final.append(df_final) # append dataframe per dataframe to the list

    dataframes_final = [dataframe for dataframe in dataframes_final if dataframe.at[0, 'Name'] in outlined_buildings]

    if buildings_update:
        for building_update in buildings_update:
            building_name = building_update['building_name']
            area_coverage_pv = building_update['area_coverage_pv']
            ev_charging = building_update['ev_charging']
            for df in dataframes_final:
                if df['Name'].iloc[0] == building_name:
                    print('Changing building', building_name)
                    # Multiply the values in the specified columns
                    df['E_PV_gen_kWh'] *= area_coverage_pv / 100
                    df['PV_Investment_€'] *= area_coverage_pv / 100
                    df['PV_Power_W'] *= area_coverage_pv / 100
                    break

    dff=dataframes_final[0] # example of calling the first dataframe from the list
    EC = dff[["Date"]].copy() # create a dataframe with only the first column by copying it

    for dataframe_final in dataframes_final: # loop on the several building files (dataframes) to perform the operations 
        dataframe_final['Enet1_'+dataframe_final["Name"][0]]=dataframe_final['GRID_kWh']-dataframe_final['E_PV_gen_kWh'] # give the name of the building and perform the calculation 
        EC['Enet1_'+dataframe_final["Name"][0]]=dataframe_final['Enet1_'+dataframe_final["Name"][0]] # consider the previous columns on just one dataframe

    EC=EC.set_index("Date") #set date as index (not a column)

    EC['EC_demand']=EC[EC>0].sum(1) # it sums all the lines and as we only have Enets it is ok.
    EC['EC_surplus']=EC[EC<0].sum(1)

    dff2=dataframes_final[0] # example of calling the first dataframe from the list
    EC_dem_gen= dff2[["Date"]].copy() # create a dataframe with only the first column by copying it

    for dataframe_final in dataframes_final: # loop on the several building files (dataframes) to perform the operations 
        dataframe_final['Edem_'+dataframe_final["Name"][0]]=dataframe_final['GRID_kWh']
        EC_dem_gen['Edem_'+dataframe_final["Name"][0]]=dataframe_final['Edem_'+dataframe_final["Name"][0]]
        dataframe_final['Egen_'+dataframe_final["Name"][0]]=dataframe_final['E_PV_gen_kWh']
        EC_dem_gen['Egen_'+dataframe_final["Name"][0]]=dataframe_final['Egen_'+dataframe_final["Name"][0]]

    EC_dem_gen['GRID_total']= EC_dem_gen[list(EC_dem_gen.filter(regex='Edem_'))].sum(axis=1)
    EC_dem_gen['PV_total']= EC_dem_gen[list(EC_dem_gen.filter(regex='Egen_'))].sum(axis=1)
    #EC_total['EC_demand_total']=EC['EC_demand']
    #EC_total['EC_surplus_total']=abs(EC['EC_surplus'])

    EC_dem=EC[['EC_demand','EC_surplus']]

    EC_hourly=pd.merge(EC_dem_gen,EC_dem,left_index=True,right_index=True,how='left')


    # EC_hourly.head(2)

    # EC_hourly.to_csv('EC_hourly_gen_dem.csv')

    #EC_to_grid:
    conditions = [
    (EC['EC_surplus']+EC['EC_demand']<0),
    (EC['EC_surplus']+EC['EC_demand']>0)
    ]
    choices = [
    (-(EC['EC_surplus']+EC['EC_demand'])),
    0]
    EC["EC_to_GRID"] = np.select(conditions, choices)

    #grid_to_EC:
    conditions2 = [
    (EC['EC_surplus']+EC['EC_demand']>0),
    (EC['EC_surplus']+EC['EC_demand']<0)
    ]
    choices2 = [
    (EC['EC_demand']+EC['EC_surplus']),
    0]

    EC["GRID_to_EC"] = np.select(conditions2, choices2)

    EC.reset_index(inplace=True) # to do easily the merge that follows

    # EC.head(4)

    EC2=EC[['EC_demand','EC_to_GRID','GRID_to_EC','EC_surplus']]

    dataframes_final2 = [] #empty list

    for dataframe_final in dataframes_final: 
        dataframe_final_vf = pd.merge(dataframe_final,EC2,left_index=True,right_index=True,how='left')
        dataframes_final2.append(dataframe_final_vf)

#-----------------------------------------------------------------------------

# Option 1 SHARE BY DEMAND
    if dropdownValue == 'By Demand':
        print('By Demand')
        for dataframe_final in dataframes_final2: 
            conditions3 = [
            (dataframe_final['Enet1_'+dataframe_final["Name"][0]]>0),
            (dataframe_final['Enet1_'+dataframe_final["Name"][0]]<0)
            ]
            choices3 = [
            (dataframe_final['Enet1_'+dataframe_final["Name"][0]])/dataframe_final['EC_demand'],
            0]
            dataframe_final['X_'+dataframe_final["Name"][0]] = np.select(conditions3, choices3)


# Option 2 SHARE BY ELEC PRODUCED

# o surplus é distribuido de acordo com a energia produzida pelos edíficios que na hora i têm procura de energia. Assim o que é considerado é identificar
# se na hora i a Enet>o e o edificio tem PV (visto pelo 'E_PV_Sum')

    elif dropdownValue == 'By Electricity Production':
        # Número de linhas nos dataframes (assumindo que todos tenham o mesmo número de linhas)
        num_linhas = len(dataframes_final2[0])
        
        # Percorre cada linha
        for i in range(num_linhas):
            # Calcula a soma das colunas E_PV das outras dataframes para a linha i, onde Enet for positivo
            E_PV_sum_total= 0
            for df in dataframes_final2:
                enet_col = 'Enet1_' + df["Name"][0]
                if df[enet_col].iloc[i] > 0:
                    E_PV_sum_total += df['E_PV_Sum'].iloc[i]
            
            # Adiciona a nova coluna com o quociente E_PV/E_PV_sum a cada dataframe
            for df in dataframes_final2:
                enet_col = 'Enet1_' + df["Name"][0]
                if df[enet_col].iloc[i] > 0 and E_PV_sum_total != 0:
                    df.at[i,'X_'+df["Name"][0]] = df['E_PV_Sum'].iloc[i] / E_PV_sum_total# acho que se pode tirar o loop do df['E_PV_Sum']
                else:
                    df.at[i,'X_'+df["Name"][0]] = 0
                
        #         df.at[i,'X_'+df["Name"][i]] = df.at[i, 'E_PV_ratio']

#---------
    for dataframe_final in dataframes_final2: 
        conditions4 = [
        (dataframe_final['Enet1_'+dataframe_final["Name"][0]]>0) & (dataframe_final['Enet1_'+dataframe_final["Name"][0]]+(dataframe_final['EC_surplus']*dataframe_final['X_'+dataframe_final["Name"][0]])>0)
        ,
        (dataframe_final['X_'+dataframe_final["Name"][0]]<0)
        ]
        choices4 = [
        (dataframe_final['Enet1_'+dataframe_final["Name"][0]])+dataframe_final['EC_surplus']* dataframe_final['X_'+dataframe_final["Name"][0]],
        0]
        dataframe_final['Egrid_'+dataframe_final["Name"][0]] = np.select(conditions4, choices4)
                    
# --------------------------------------------------------------------



    # calculate the daily average consumption value for sizing the battery

    # EC

    EC2=EC_hourly.copy()
    EC2['Date'] = pd.to_datetime(EC2['Date'])

    # # Definindo 'Date' como índice para facilitar o agrupamento
    EC2.set_index('Date', inplace=True)


    daily_sum_consumption = EC2['GRID_total'].resample('D').sum()
    average_daily_consumption_year = daily_sum_consumption.mean()


    # average_daily_consumption_year

    CAPACITY_kWh=average_daily_consumption_year * battery_efficiency #average daily demand
    SOCMAX=0.95
    SOCMAX_kWh=SOCMAX*CAPACITY_kWh
    SOCMIN=0.10
    SOCMIN_kWh=SOCMIN*CAPACITY_kWh
    EFF=0.95 
    NOM_CAP=0.33
    NOM_CAP_kWh=NOM_CAP*CAPACITY_kWh

    GRID_to_EC_withoutB=EC['GRID_to_EC'].agg(lambda x : x.sum())
    EC_to_GRID_withoutB=EC['EC_to_GRID'].agg(lambda x : x.sum())

    daily_gridtoEC=(GRID_to_EC_withoutB/365)
    daily_ECtogrid=EC_to_GRID_withoutB/365

    coverage=1
    batcap=daily_gridtoEC*coverage/(SOCMAX-SOCMIN)
    batcap_gen=daily_ECtogrid*coverage/(SOCMAX-SOCMIN)
    batcap,batcap_gen, daily_gridtoEC,daily_ECtogrid,EC_to_GRID_withoutB

    EC['EFF']=0.95
    EC['NOM_CAP_kWh']=NOM_CAP_kWh
    EC.loc[-1,'SOC']=SOCMAX_kWh

    for i in range(0,8760):
        # STEP 9
        EC.at[i,'ESOC_D'] = max(EC.at[i-1,'SOC']-SOCMIN_kWh,0) 
        
        # STEP 10
        EC.at[i,'ESOC_C'] = max(SOCMAX_kWh-EC.at[i-1,'SOC'],0) 
        
        # STEP 11
        if (EC.at[i,'ESOC_D'] > EC.at[i,'GRID_to_EC']):
            EC.at[i,'DISC'] = min(EC.at[i,'GRID_to_EC']/EFF,NOM_CAP_kWh)
        else:
            EC.at[i,'DISC'] = min(EC.at[i,'ESOC_D']/EFF,NOM_CAP_kWh)

        # STEP 12
        if (EC.at[i,'ESOC_C'] > EC.at[i,'EC_to_GRID']):
            EC.at[i, 'CHAR'] = min(EC.at[i,'EC_to_GRID']*EFF, NOM_CAP_kWh)
        else:
            EC.at[i,'CHAR'] = min(EC.at[i,'ESOC_C']*EFF,NOM_CAP_kWh)    
        
        #STEP 13:
        if(EC.at[i,'DISC']>0):
            EC.at[i,'SOC']=max(EC.at[i-1,'SOC']-EC.at[i,'DISC'],SOCMIN_kWh)
        else:
            EC.at[i,'SOC']=min(EC.at[i-1,'SOC']+EC.at[i,'CHAR'],SOCMAX_kWh)

    for i in range(0,8760):
        curr_line = EC.loc[i]
        # Step 14
        EC.at[i,'EC_to_GRID_B']=max(curr_line.at['EC_to_GRID']-curr_line.at['CHAR'],0)
        # Step 15
        EC.at[i,'GRID_to_EC_B']=max(curr_line.at['GRID_to_EC']-curr_line.at['DISC'],0)    

    # EC.to_csv('EC_bess.csv')

    dataframes_final3 = [] #empty list
    for dataframe_final in dataframes_final2: 
        dataframe_final = pd.merge(dataframe_final,EC[['GRID_to_EC_B','EC_to_GRID_B']],left_index=True,right_index=True,how='left')
        dataframes_final3.append(dataframe_final)
        

    for dataframe_final in dataframes_final3: 
        dataframe_final['EgridBESS_'+dataframe_final["Name"][0]] = dataframe_final['X_'+dataframe_final["Name"][0]]*dataframe_final['GRID_to_EC_B']
        

    #EC TARIFF


    tariff = pd.read_csv('tariffs_imb.csv', sep =',')

    tariff.reset_index(inplace=True) # to do easily the merge that dollows

    dataframes_final4=[]
    for dataframe_final in dataframes_final3: 
        dataframe_final = pd.concat([dataframe_final,tariff],axis=1) # add the day type and months for the savings calculation
        dataframes_final4.append(dataframe_final)

    #for dataframe_final in dataframes_final4:
    #    dataframe_final['Cost_SC'[0]] = dataframe_final['Enet1_'+dataframe_final["Name"][0]]*dataframe_final['Tariff_self_cons']

    #for dataframe_final in dataframes_final4:
    #   dataframe_final['Cost_EC'[0]]=dataframe_final['Egrid_'+dataframe_final["Name"][0]]*dataframe_final['Tariff_EC']

    # dataframes_final4[0].to_csv('EC_d1bfinal.csv')

    for dataframe_final in dataframes_final4:
        dataframe_final['Cost_base']=dataframe_final['GRID_kWh']*dataframe_final['Tariff_base']
        dataframe_final['Cost_SC'] = dataframe_final['Enet1_'+dataframe_final["Name"][0]]*dataframe_final['Tariff_self_cons']
        dataframe_final['Cost_EC']=dataframe_final['Egrid_'+dataframe_final["Name"][0]]*dataframe_final['Tariff_EC']
        dataframe_final['Cost_EC_BESS']=dataframe_final['EgridBESS_'+dataframe_final["Name"][0]]*dataframe_final['Tariff_EC_BESS']
        dataframe_final['Income'] =dataframe_final['Enet1_'+dataframe_final["Name"][0]]*dataframe_final['Tariff_surp']
        dataframe_final['Income_EC'] =dataframe_final['EC_to_GRID']*dataframe_final['Tariff_surp']
        dataframe_final['Income_EC_B'] =dataframe_final['EC_to_GRID_B']*dataframe_final['Tariff_surp']

    B_savings=[]
    for dataframe_final in dataframes_final4: 
        B_savings.append(dataframe_final["Name"][0])
        
    B_savings = pd.DataFrame({"Building":B_savings})   

    B_savings.head(2)

    for dataframe_final in dataframes_final4:
        locals()["Total_cost_base"+ str(dataframe_final["Name"][0])]= dataframe_final['Cost_base'].agg(lambda x : x.sum())
        locals()["Total_cost_SC"+ str(dataframe_final["Name"][0])]= dataframe_final['Cost_SC'].agg(lambda x : x[x > 0].sum())
        locals()["Total_cost_EC"+ str(dataframe_final["Name"][0])]= dataframe_final['Cost_EC'].agg(lambda x : x.sum())
        locals()["Total_cost_EC_BESS"+ str(dataframe_final["Name"][0])]= dataframe_final['Cost_EC_BESS'].agg(lambda x : x.sum())
        locals()["Income_PV"+ str(dataframe_final["Name"][0])]=-1*( dataframe_final['Income'].agg(lambda x : x[x < 0].sum()))
        locals()["Surpluses"+ str(dataframe_final["Name"][0])]=abs(dataframe_final['Enet1_'+dataframe_final["Name"][0]].agg(lambda x : x[x < 0].sum()))
        locals()["SurpluesEC"+ str(dataframe_final["Name"][0])]= dataframe_final['EC_to_GRID'].agg(lambda x : x.sum())
        locals()["SurpluesEC_B"+ str(dataframe_final["Name"][0])]= dataframe_final['EC_to_GRID_B'].agg(lambda x : x.sum())
        locals()["Income_EC_total"+ str(dataframe_final["Name"][0])]= dataframe_final['Income_EC'].agg(lambda x : x.sum())
        locals()["Income_EC_B_total"+ str(dataframe_final["Name"][0])]= dataframe_final['Income_EC_B'].agg(lambda x : x.sum())
        locals()["PV_Power_W"+ str(dataframe_final["Name"][0])]= dataframe_final['PV_Power_W'][0]
        locals()["PV_Investment_€"+ str(dataframe_final["Name"][0])]= dataframe_final['PV_Investment_€'][0]

    for i in range(len(B_savings)):
        B_savings.loc[i,'Ecost_base (€)']=locals()["Total_cost_base"+B_savings.loc[i,'Building']]
        B_savings.loc[i,'Ecost_SC (€)']=locals()["Total_cost_SC"+B_savings.loc[i,'Building']]
        B_savings.loc[i,'Ecost_EC (€)']=locals()["Total_cost_EC"+B_savings.loc[i,'Building']]
        B_savings.loc[i,'Ecost_EC_BESS (€)']=locals()["Total_cost_EC_BESS"+B_savings.loc[i,'Building']]
        B_savings.loc[i,'Savings_SC (€)']=locals()["Total_cost_base"+B_savings.loc[i,'Building']]-locals()["Total_cost_SC"+B_savings.loc[i,'Building']]
        B_savings.loc[i,'Savings_SC (%)']=(locals()["Total_cost_base"+B_savings.loc[i,'Building']]-locals()["Total_cost_SC"+B_savings.loc[i,'Building']])/(locals()["Total_cost_base"+B_savings.loc[i,'Building']])
        B_savings.loc[i,'Savings_EC (€)']=locals()["Total_cost_base"+B_savings.loc[i,'Building']]-locals()["Total_cost_EC"+B_savings.loc[i,'Building']]
        B_savings.loc[i,'Savings_EC (%)']=(locals()["Total_cost_base"+B_savings.loc[i,'Building']]-locals()["Total_cost_EC"+B_savings.loc[i,'Building']])/(locals()["Total_cost_base"+B_savings.loc[i,'Building']])
        B_savings.loc[i,'Savings_EC_BESS (€)']=locals()["Total_cost_base"+B_savings.loc[i,'Building']]-locals()["Total_cost_EC_BESS"+B_savings.loc[i,'Building']]
        B_savings.loc[i,'Savings_EC_BESS (%)']=(locals()["Total_cost_base"+B_savings.loc[i,'Building']]-locals()["Total_cost_EC_BESS"+B_savings.loc[i,'Building']])/(locals()["Total_cost_base"+B_savings.loc[i,'Building']])
        B_savings.loc[i,'Income_PV_SC(€)']=locals()["Income_PV"+B_savings.loc[i,'Building']]
        B_savings.loc[i,'Income_PV_EC(€)']=locals()["Surpluses"+B_savings.loc[i,'Building']]/locals()["SurpluesEC"+B_savings.loc[i,'Building']]*locals()["Income_EC_total"+B_savings.loc[i,'Building']]
        B_savings.loc[i,'Income_PV_EC_B(€)']=locals()["Surpluses"+B_savings.loc[i,'Building']]/locals()["SurpluesEC_B"+B_savings.loc[i,'Building']]*locals()["Income_EC_B_total"+B_savings.loc[i,'Building']]
        B_savings.loc[i,'incomeEC_total']=locals()["Income_EC_total"+B_savings.loc[i,'Building']]
        B_savings.loc[i,'incomeEC_b_total']=locals()["Income_EC_B_total"+B_savings.loc[i,'Building']]
        B_savings.loc[i,'PV_Power_W']=locals()["PV_Power_W"+B_savings.loc[i,'Building']]
        B_savings.loc[i,'PV_Investment_€']=locals()["PV_Investment_€"+B_savings.loc[i,'Building']]

    B_savings.head(2)

    # B_savings.to_csv('EC_building_savings.csv')

    #don't consider the columns created with random letters, was only confirming step by step the calculations.
    #here there's an error in the last columns : Income EC_total and income EC_B_total
    #the total should be 2803 and 2394 
    #nevertheless,FOR OTHER BUILDINGS the total is 2779 and 2370. 
    #the total income should be the same for all the cases bc EC_to_Grid and EC_to_Grid_B should be the same in all folders. 
    #i can't find where is the error, the operation is exactly the same
    #Ec_to_grid is the same in all folders, and tariff_surplus also, dont understand why at the end the sum in not the same. makes no sense.

    E_total_cost_base=B_savings['Ecost_base (€)'].agg(lambda x : x.sum())
    E_total_cost_SC=B_savings['Ecost_SC (€)'].agg(lambda x : x.sum())
    E_total_cost_EC=B_savings['Ecost_EC (€)'].agg(lambda x : x.sum())
    E_total_cost_EC_B=B_savings['Ecost_EC_BESS (€)'].agg(lambda x : x.sum())
    E_total_income_EC=B_savings['Income_PV_EC(€)'].agg(lambda x : x.sum())
    E_total_income_EC_B=B_savings['Income_PV_EC_B(€)'].agg(lambda x : x.sum())

    EC_total_savings = pd.DataFrame()

    EC_total_savings.loc[0,'Energy_cost_base (€)']=E_total_cost_base
    EC_total_savings.loc[0,'Energy_cost_EC (€)']=E_total_cost_EC
    EC_total_savings.loc[0,'Savings (€)']=E_total_cost_base - E_total_cost_EC
    EC_total_savings.loc[0,'Savings (%)']=(E_total_cost_base - E_total_cost_EC)/E_total_cost_base
    EC_total_savings.loc[0,'Income_PV_total(€)']=E_total_income_EC

    EC_total_savings.loc[1,'Energy_cost_base (€)']=E_total_cost_base
    EC_total_savings.loc[1,'Energy_cost_EC (€)']=E_total_cost_EC_B
    EC_total_savings.loc[1,'Savings (€)']=E_total_cost_base - E_total_cost_EC_B
    EC_total_savings.loc[1,'Savings (%)']=(E_total_cost_base - E_total_cost_EC_B)/E_total_cost_base
    EC_total_savings.loc[1,'Income_PV_total(€)']=E_total_income_EC_B

    EC_total_savings.rename(index={0: 'Without BESS',1:'With BESS'},inplace=True)

    EC_total_savings

    # EC_total_savings.to_csv('EC_total_savings.csv')

    EC_analysis=[]
    for dataframe_final in dataframes_final3: 
        EC_analysis.append(dataframe_final["Name"][0])
        
    EC_analysis = pd.DataFrame({"Building":EC_analysis})                                             

    for dataframe_final in dataframes_final3:
        locals()["EC_"+ str(dataframe_final["Name"][0])]= dataframe_final['Enet1_'+dataframe_final["Name"][0]].agg(lambda x : x[x > 0].sum())
        locals()["Egrid_"+ str(dataframe_final["Name"][0])]= dataframe_final['Egrid_'+dataframe_final["Name"][0]].agg(lambda x : x.sum())
        locals()["ECgridBESS_"+ str(dataframe_final["Name"][0])]= dataframe_final['EgridBESS_'+dataframe_final["Name"][0]].agg(lambda x : x.sum())
        locals()["GRID_kWh_"+ str(dataframe_final["Name"][0])]= dataframe_final['GRID_kWh'].agg(lambda x : x.sum())
        
        locals()["PV_gen(kWh/year)_"+ str(dataframe_final["Name"][0])]= dataframe_final['E_PV_gen_kWh'].agg(lambda x : x.sum())
        locals()["SURPLUS_"+ str(dataframe_final["Name"][0])]= abs(dataframe_final['Enet1_'+dataframe_final["Name"][0]].agg(lambda x : x[x < 0].sum()))
        locals()["Self_consumed_energy_"+ str(dataframe_final["Name"][0])]=  locals()["PV_gen(kWh/year)_"+ str(dataframe_final["Name"][0])]-locals()["SURPLUS_"+ str(dataframe_final["Name"][0])]
        #demand
        locals()["Demand_"+ str(dataframe_final["Name"][0])]= dataframe_final['GRID_kWh'].agg(lambda x : x.sum())


    for i in range(len(EC_analysis)):
        EC_analysis.loc[i,'Demand (kWh/year)']=locals()["Demand_"+EC_analysis.loc[i,'Building']]
        
        EC_analysis.loc[i,'PV_gen(kWh/year)']=locals()["PV_gen(kWh/year)_"+EC_analysis.loc[i,'Building']]
        
        EC_analysis.loc[i,'SELFCONS (kWh/year)']=locals()["EC_"+EC_analysis.loc[i,'Building']]
        EC_analysis.loc[i,'SELFCONS (SS RATIO)']=1-EC_analysis.loc[i,'SELFCONS (kWh/year)']/locals()["GRID_kWh_"+EC_analysis.loc[i,'Building']]
        
        EC_analysis.loc[i,'EC_SHARING (kWh/year)']=locals()["Egrid_"+EC_analysis.loc[i,'Building']]
        EC_analysis.loc[i,'EC_SHARING (SS RATIO)']= 1-EC_analysis.loc[i,'EC_SHARING (kWh/year)']/locals()["GRID_kWh_"+EC_analysis.loc[i,'Building']]
        
        EC_analysis.loc[i,'EC_BESS (kWh/year)']=locals()["ECgridBESS_"+EC_analysis.loc[i,'Building']]
        EC_analysis.loc[i,'EC_BESS (SS RATIO)']=1- EC_analysis.loc[i,'EC_BESS (kWh/year)']/locals()["GRID_kWh_"+EC_analysis.loc[i,'Building']]
        

        EC_analysis.loc[i,'Self_consumed_energy (kWh/year)']=locals()["Self_consumed_energy_"+EC_analysis.loc[i,'Building']]
        
    # EC_analysis

    # EC_analysis.to_csv('EC_analysis_buildings.csv')

    Demand=EC_analysis['Demand (kWh/year)'].agg(lambda x : x.sum())

    PV_gen_kWh_year= EC_analysis['PV_gen(kWh/year)'].agg(lambda x : x.sum())

    EC_to_GRID_withoutB=EC['EC_to_GRID'].agg(lambda x : x.sum())

    EC_Self_consumed_energy_withoutB=PV_gen_kWh_year-EC_to_GRID_withoutB

    GRID_to_EC_withoutB=EC['GRID_to_EC'].agg(lambda x : x.sum())

    EC_total = pd.DataFrame()

    EC_total.loc[0,'Demand_(kWh_year)']=Demand
    EC_total.loc[0,'PV_gen_(kWh_year)']=PV_gen_kWh_year
    EC_total.loc[0,'EC_to_GRID_(kWh_year)']=EC_to_GRID_withoutB
    EC_total.loc[0,'EC_Self_consumed_energy_(kWh_year)']=EC_Self_consumed_energy_withoutB
    EC_total.loc[0,'SC RATIO(%)']=EC_Self_consumed_energy_withoutB/PV_gen_kWh_year
    EC_total.loc[0,'GRID_to_EC_(kWh_year)']=GRID_to_EC_withoutB
    EC_total.loc[0,'SS RATIO(%)']=1-(GRID_to_EC_withoutB/Demand)

    # Demand is the same

    # PV_gen_kWh_year is the same

    EC_to_GRID_withB=EC['EC_to_GRID_B'].agg(lambda x : x.sum())

    EC_Self_consumed_energy_withB=PV_gen_kWh_year-EC_to_GRID_withB

    GRID_to_EC_withB=EC['GRID_to_EC_B'].agg(lambda x : x.sum())

    SOC_sum=EC['SOC'].agg(lambda x : x.sum())

    EC_total.loc[1,'Demand_(kWh_year)']=Demand
    EC_total.loc[1,'PV_gen_(kWh_year)']=PV_gen_kWh_year
    EC_total.loc[1,'EC_to_GRID_(kWh_year)']=EC_to_GRID_withB
    EC_total.loc[1,'EC_Self_consumed_energy_(kWh_year)']=EC_Self_consumed_energy_withB
    EC_total.loc[1,'SC RATIO(%)']=EC_Self_consumed_energy_withB/PV_gen_kWh_year
    EC_total.loc[1,'GRID_to_EC_(kWh_year)']=GRID_to_EC_withB
    EC_total.loc[1,'SS RATIO(%)']=1-(GRID_to_EC_withB/Demand)
    EC_total.loc[1,'AVERAGE SOC(%)']=(SOC_sum-SOCMAX_kWh)/8760/CAPACITY_kWh

    EC_total.rename(index={0: 'Without BESS',1:'With BESS'},inplace=True)

    # EC_total.to_csv('EC_analysis_total.csv')

    # Figures

    return create_figures(EC_total, B_savings, outlined_buildings)

def create_figures(energy_consumption=None, buildings_savings=None, outlined_buildings=[]):
    """
    Create all figures needed for dashboard
    """
    if energy_consumption is None:
        energy_consumption = pd.read_csv('viana_do_castelo/EC_analysis_total.csv', usecols=['SS RATIO(%)', 'SC RATIO(%)'])
        energy_consumption.rename(index={0: 'Without BESS', 1:'With BESS'},inplace=True)
    if buildings_savings is None:
        buildings_savings = pd.read_csv('viana_do_castelo/EC_building_savings.csv', usecols=['Building', 'Ecost_base (€)', 'Ecost_SC (€)', 'Ecost_EC (€)', 'Ecost_EC_BESS (€)','PV_Power_W','PV_Investment_€'])
        buildings_savings.set_index('Building')

    consumption_columns = ['SS RATIO(%)', 'SC RATIO(%)']
    ec_figure = px.bar(energy_consumption[consumption_columns], barmode='group', height=950,title="Self-consumption and self-sufficiency")

    renamed_columns = {
        'Ecost_base (€)': 'Custo de electricidade sem CE (€)',
        'Ecost_SC (€)': 'Custo de electricidade com PV sem CE (€)',
        'Ecost_EC (€)': 'Custo de electricidade com PV em CE (€)',
        'Ecost_EC_BESS (€)': 'Custo de electricidade com PV e bateria em CE (€)'
    }

    # Rename the columns in the DataFrame
    B_savings_renamed = buildings_savings.rename(columns=renamed_columns)
    
    bs_figure = px.bar(
        B_savings_renamed,
        x='Building',
        y=list(renamed_columns.values()),
        barmode='group',
        height=950,
        title="Energy costs annually"
    )

    pv_columns = {
        'PV_Power_W': 'Potência do sistema fotovoltaico (W)',
        'PV_Investment_€': 'Investimento do sistema fotovoltaico (€)'
    }

    # Rename the columns in the DataFrame
    B_savings_renamed = buildings_savings.rename(columns=pv_columns)

    PV_figure = px.bar(
        B_savings_renamed,
        x='Building',
        y=list(pv_columns.values()),
        barmode='group',
        height=950,
        title="PV Power and Investment"
    )

    if buildings_savings is None:
        buildings_savings = pd.read_csv('viana_do_castelo/EC_building_savings.csv', usecols=['Building', 'Ecost_base (€)', 'Ecost_SC (€)', 'Ecost_EC (€)', 'Ecost_EC_BESS (€)'])
    buildings_savings.set_index('Building')
    buildings_shapefile = gpd.read_file('viana_do_castelo/zone.shp')
    gdf = buildings_shapefile.merge(buildings_savings,left_on='Name', right_on='Building',how='right')
    gdf = gdf.to_crs(epsg=4326)

    map2d_figure = px.choropleth_mapbox(
        gdf,
        geojson=gdf.geometry,
        locations=gdf.index,
        color='Ecost_base (€)',
        hover_data={'Building','Ecost_base (€)','Ecost_SC (€)', 'Ecost_EC_BESS (€)'},
        center={'lat': 41.68307857293268, 'lon': -8.821966245912416},  
        mapbox_style='open-street-map',
        zoom=16,
        width=1000,
        height=1300,
        title= "Annual Energy Cost (select a building set to run an EC analysis)"
    )

    map3d_figure = create_map(gdf, outlined_buildings)

    return map3d_figure, map2d_figure, ec_figure, bs_figure, PV_figure

def interpolate_color(value, colormap=plasma_colormap):
    """
    Linearly interpolate between colors in a colormap.

    Parameters:
        value (float): A normalized float (0 to 1) indicating position along the colormap.
        colormap (list): A list of RGBA colors as [R, G, B, A].

    Returns:
        color (list): Interpolated RGBA color.
    """
    if value < 0: value = 0
    if value > 1: value = 1
    
    # Find which two colors to interpolate between
    num_colors = len(colormap)
    idx = int(value * (num_colors - 1))  # Get index
    t = (value * (num_colors - 1)) - idx  # Interpolation factor between idx and idx + 1
    
    # Interpolate between two colors
    color1 = np.array(colormap[idx])
    color2 = np.array(colormap[min(idx + 1, num_colors - 1)])
    
    # Linear interpolation between color1 and color2
    color = (1 - t) * color1 + t * color2
    return [int(c) for c in color]

def create_map(gdf=None, outlined_buildings=[], previous_layer=None):
    if gdf is None:
        buildings_savings = pd.read_csv('viana_do_castelo/EC_building_savings.csv', usecols=['Building', 'Ecost_base (€)', 'Ecost_SC (€)', 'Ecost_EC (€)', 'Ecost_EC_BESS (€)'])
        buildings_savings.set_index('Building')
        buildings_shapefile = gpd.read_file('viana_do_castelo/zone.shp')
        gdf = buildings_shapefile.merge(buildings_savings,left_on='Name', right_on='Building',how='right')
        gdf = gdf.to_crs(epsg=4326)

    gdf['fill_color'] = (gdf['Ecost_base (€)'] - gdf['Ecost_base (€)'].min()) / (gdf['Ecost_base (€)'].max() - gdf['Ecost_base (€)'].min()) # normalize cost between 0-1
    gdf['fill_color'] = gdf['fill_color'].apply(interpolate_color)

    # If buildings are selected, change their outline color to visually indicate selection
    gdf['line_color'] = gdf.apply(
        lambda row: [255, 0, 0, 255] if row['Building'] in outlined_buildings else [255, 255, 255, 255], axis=1
    )
    view_state = pdk.ViewState(
        **{
            "latitude": 41.68307857293268,
            "longitude": -8.821966245912416,
            "zoom": 16,
            "maxZoom": 20,
            "pitch": 45,
            "bearing": 0,
        }
    )

    if previous_layer is None:
        # Layer for extruded buildings
        extruded_layer = pdk.Layer(
            "GeoJsonLayer",
            gdf,
            opacity=0.8,
            stroked=False,  # Disable strokes for this layer
            filled=True,
            extruded=True,
            get_polygon="geometry",
            get_fill_color="fill_color",
            get_elevation="height_ag * 2",
            auto_highlight=True,
            pickable=True,
            id='extruded-layer'
        )
    else:
        extruded_layer = previous_layer

    # Separate layer for building outlines (non-extruded)
    outline_layer = pdk.Layer(
        "GeoJsonLayer",
        gdf,
        opacity=1,
        stroked=True,  # Enable strokes for this layer
        filled=False,  # Disable fill for this layer
        extruded=False,  # Ensure outlines are 2D
        get_polygon="geometry",
        get_line_color="line_color",
        line_width_min_pixels=3,  # Set outline thickness
    )

    map = pdk.Deck(
        [extruded_layer, outline_layer],  # Stack the layers
        initial_view_state=view_state,
        map_style=pdk.map_styles.LIGHT,
    )

    return map.to_json()