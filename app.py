import os
import numpy as np
import pandas as pd
import altair as alt
import streamlit as st
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error
import storage

st.set_page_config(page_title='Energia em Foco | Projeto Integrador',page_icon='⚡',layout='wide')
st.markdown('''<style>
.block-container{max-width:1160px;padding-top:1.5rem}
[data-testid="stMetric"]{background:rgba(90,120,150,.11);border:1px solid rgba(125,125,125,.18);border-radius:12px;padding:16px}
[data-testid="stMetricLabel"], [data-testid="stMetricValue"]{color:inherit!important}
</style>''',unsafe_allow_html=True)
MONTHS=['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro']
SHORT=['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
DEMO=pd.DataFrame({'mes':pd.date_range('2025-01-01',periods=24,freq='MS'),'consumo_kwh':[270,260,275,245,235,230,245,255,270,285,300,330,290,275,280,260,245,240,250,265,280,300,320,345],'tarifa':[.9]*24})

def money(n): return 'R$ '+f'{n:,.2f}'.replace(',','X').replace('.',',').replace('X','.')
def num(n,d=1): return f'{n:,.{d}f}'.replace(',','X').replace('.',',').replace('X','.')
def flash(msg): st.session_state.notice=msg
def rerun_notice():
    if st.session_state.get('notice'): st.success(st.session_state.pop('notice'))

def init():
    defaults={'mode':'home','uid':None,'username':None,'demo':DEMO.copy(),'page':'Painel inicial'}
    for k,v in defaults.items():
        if k not in st.session_state: st.session_state[k]=v
init()

def records():
    if st.session_state.mode=='demo': return st.session_state.demo.copy()
    try:
        rows=storage.get_records(st.session_state.uid)
        df=pd.DataFrame(rows,columns=['mes','consumo_kwh','tarifa'])
        if not df.empty: df.mes=pd.to_datetime(df.mes)
        return df
    except Exception:
        st.error('Não foi possível consultar os dados. Verifique a conexão com o banco.'); st.stop()

def home():
    st.title('⚡ Energia em Foco')
    st.subheader('Entenda seu consumo. Economize com inteligência.')
    st.write('Projeto Integrador acadêmico de análise de consumo residencial de energia.')
    a,b=st.columns(2,gap='large')
    with a:
        st.markdown('### 👀 Experimentar demonstração')
        st.write('Conheça gráficos, previsões e simulador com dados fictícios. Não é necessário cadastro. As alterações são temporárias.')
        if st.button('Experimentar sem cadastro',type='primary',use_container_width=True):
            st.session_state.mode='demo'; st.session_state.demo=DEMO.copy();st.session_state.page='Painel inicial';st.rerun()
    with b:
        st.markdown('### 👤 Minha conta')
        st.write('Crie um nome de usuário e uma senha para salvar seu histórico. Não solicitamos e-mail, CPF ou telefone.')
        t1,t2=st.tabs(['Entrar','Criar conta'])
        with t1:
            with st.form('login'):
                u=st.text_input('Nome de usuário',key='login_u')
                p=st.text_input('Senha',type='password',key='login_p')
                if st.form_submit_button('Entrar',type='primary'):
                    try:
                        uid=storage.authenticate(u,p)
                        if uid:
                            st.session_state.uid=uid;st.session_state.username=u.strip().lower();st.session_state.mode='account';st.session_state.page='Painel inicial';st.rerun()
                        else: st.error('Usuário ou senha incorretos.')
                    except Exception: st.error('Erro ao acessar o banco. Confira a configuração.')
        with t2:
            with st.form('signup'):
                u=st.text_input('Escolha um usuário (3 a 30 caracteres)')
                p=st.text_input('Crie uma senha (mínimo 8 caracteres)',type='password')
                p2=st.text_input('Confirme sua senha',type='password')
                if st.form_submit_button('Criar minha conta'):
                    if p!=p2: st.error('As senhas não coincidem.')
                    else:
                        try:
                            storage.register(u,p);st.success('Conta criada! Entre na aba Entrar usando seu usuário e senha.')
                        except ValueError as e: st.warning(str(e))
                        except Exception:
                            st.error('Erro ao cadastrar. Tente novamente mais tarde.')
    st.info('Sem e-mail, não é possível recuperar automaticamente a senha. Guarde suas credenciais. Você pode excluir a conta e exportar seus dados.')
    if not storage.cloud(): st.caption('Executando com banco local SQLite. Para que contas funcionem no site publicado, configure o Supabase conforme o guia.')

if st.session_state.mode=='home':
    home();st.stop()

with st.sidebar:
    st.title('⚡ Energia em Foco')
    st.caption('Seu consumo, suas escolhas')
    st.info('Demonstração • dados fictícios' if st.session_state.mode=='demo' else 'Minha conta • '+st.session_state.username)
    pages=['Painel inicial','Meus consumos','Previsão','Simulador de economia','Sobre o projeto']
    page=st.radio('Navegação',pages,index=pages.index(st.session_state.page),label_visibility='collapsed')
    st.session_state.page=page
    st.divider()
    months=st.slider('Meses para previsão',1,12,3)
    if st.button('Sair / voltar ao início',use_container_width=True):
        st.session_state.mode='home';st.session_state.uid=None;st.session_state.username=None;st.session_state.demo=DEMO.copy();st.rerun()

df=records().sort_values('mes').reset_index(drop=True)
if not df.empty:
    df['mes']=pd.to_datetime(df['mes']);df['consumo_kwh']=pd.to_numeric(df['consumo_kwh']);df['tarifa']=pd.to_numeric(df['tarifa']);df['custo']=df.consumo_kwh*df.tarifa
st.title(page)
rerun_notice()

if page=='Painel inicial':
    st.write('Consulte seus consumos mensais, organizados por ano.')
    if df.empty: st.info('Você ainda não cadastrou consumos. Acesse “Meus consumos” para começar.')
    else:
        years=sorted(df.mes.dt.year.unique().tolist(),reverse=True)
        year=st.selectbox('Selecione o ano',years)
        annual=df[df.mes.dt.year==year].copy()
        a,b,c,d=st.columns(4)
        a.metric('Média mensal',num(annual.consumo_kwh.mean())+' kWh')
        b.metric('Maior consumo',num(annual.consumo_kwh.max())+' kWh')
        c.metric('Menor consumo',num(annual.consumo_kwh.min())+' kWh')
        d.metric('Gasto estimado no ano',money(annual.custo.sum()))
        st.subheader(f'Consumo mensal de {year}')
        chart=pd.DataFrame({'Mês':SHORT,'Consumo (kWh)':[float(annual.loc[annual.mes.dt.month==m,'consumo_kwh'].iloc[0]) if (annual.mes.dt.month==m).any() else np.nan for m in range(1,13)]})
        bars = alt.Chart(chart).mark_bar(color='#2187bc', size=34).encode(
            x=alt.X('Mês:N', sort=SHORT, axis=alt.Axis(title=None, labelAngle=0),
                    scale=alt.Scale(domain=SHORT)),
            y=alt.Y('Consumo (kWh):Q', scale=alt.Scale(zero=True),
                    axis=alt.Axis(title='Consumo (kWh)', format='.0f')),
            tooltip=[alt.Tooltip('Mês:N', title='Mês'),
                     alt.Tooltip('Consumo (kWh):Q', title='Consumo', format='.1f')]
        ).properties(height=360)
        st.altair_chart(bars, use_container_width=True)
        st.caption('Meses sem cadastro ficam vazios. Os indicadores consideram somente os meses registrados no ano selecionado.')
        annual['Mês']=annual.mes.dt.strftime('%m/%Y')
        annual['Custo estimado']=annual.custo.map(money)
        st.dataframe(annual[['Mês','consumo_kwh','Custo estimado']].rename(columns={'consumo_kwh':'Consumo (kWh)'}),hide_index=True,use_container_width=True)

elif page=='Meus consumos':
    st.write('Cadastre o consumo e a tarifa de cada mês. Você poderá editar ou excluir registros.')
    with st.form('record',clear_on_submit=False):
        a,b=st.columns(2)
        with a:
            year=int(st.number_input('Ano',min_value=2000,max_value=2100,value=2026,step=1))
            month=st.selectbox('Mês',range(1,13),format_func=lambda m:MONTHS[m-1])
        with b:
            kwh=st.number_input('Consumo mensal (kWh)',min_value=0.0,value=250.0,step=1.0)
            tariff=st.number_input('Tarifa estimada (R$/kWh)',min_value=0.0,value=.90,step=.01,format='%.2f')
        target=f'{year:04d}-{month:02d}-01'
        exists=not df.empty and (df.mes==pd.Timestamp(target)).any()
        if exists: st.info('Esse mês já possui um registro. Ao salvar, os valores anteriores serão substituídos.')
        if st.form_submit_button('Salvar consumo',type='primary'):
            try:
                if st.session_state.mode=='demo':
                    st.session_state.demo=st.session_state.demo[st.session_state.demo.mes!=pd.Timestamp(target)]
                    st.session_state.demo=pd.concat([st.session_state.demo,pd.DataFrame([{'mes':pd.Timestamp(target),'consumo_kwh':kwh,'tarifa':tariff}])],ignore_index=True)
                else: storage.save(st.session_state.uid,target,float(kwh),float(tariff))
                flash(f'Consumo de {MONTHS[month-1].lower()} de {year} salvo com sucesso!');st.rerun()
            except Exception: st.error('Não foi possível salvar o registro.')
    if df.empty: st.info('Ainda não há registros.')
    else:
        st.subheader('Histórico cadastrado')
        view=pd.DataFrame({'Mês':df.mes.dt.strftime('%m/%Y'),'Consumo (kWh)':df.consumo_kwh.map(lambda x:num(x,1)),'Tarifa (R$/kWh)':df.tarifa.map(lambda x:num(x,2)),'Custo estimado':df.custo.map(money)})
        st.dataframe(view,hide_index=True,use_container_width=True)
        csv=pd.DataFrame({'Mês':df.mes.dt.strftime('%m/%Y'),'Consumo (kWh)':df.consumo_kwh,'Tarifa (R$/kWh)':df.tarifa,'Custo estimado (R$)':df.custo})
        st.download_button('Baixar histórico para Excel (CSV)',csv.to_csv(index=False,sep=';',decimal=',').encode('utf-8-sig'),'energia_em_foco_historico.csv','text/csv')
        with st.expander('Excluir consumo de um mês'):
            options={d.strftime('%m/%Y'):d.strftime('%Y-%m-%d') for d in df.mes}
            selected=st.selectbox('Mês para excluir',list(options))
            confirmed=st.checkbox('Confirmo que desejo excluir esse registro')
            if st.button('Excluir mês',disabled=not confirmed):
                try:
                    if st.session_state.mode=='demo':st.session_state.demo=st.session_state.demo[st.session_state.demo.mes!=pd.Timestamp(options[selected])].copy()
                    else:storage.delete(st.session_state.uid,options[selected])
                    flash('Registro excluído com sucesso.');st.rerun()
                except Exception:st.error('Não foi possível excluir o registro.')

elif page=='Previsão':
    st.write('Estimativa estatística a partir do histórico cadastrado. Não é uma previsão climática.')
    if len(df)<3:st.warning('Cadastre pelo menos três meses para gerar uma previsão.')
    else:
        # Usa o número de meses desde a primeira observação, respeitando lacunas no histórico.
        base=df.mes.min();x=((df.mes.dt.year-base.year)*12+(df.mes.dt.month-base.month)).to_numpy().reshape(-1,1)
        y=df.consumo_kwh.to_numpy(dtype=float)
        model=LinearRegression().fit(x,y)
        dates=pd.date_range(df.mes.max()+pd.offsets.MonthBegin(1),periods=months,freq='MS')
        future=((dates.year-base.year)*12+(dates.month-base.month)).to_numpy().reshape(-1,1)
        pred=np.maximum(0,model.predict(future))
        st.subheader('Histórico e previsão')
        hist=pd.DataFrame({'Mês':df.mes.dt.strftime('%m/%Y'),'Histórico (kWh)':y,'Previsão (kWh)':np.nan})
        pred_df=pd.DataFrame({'Mês':dates.strftime('%m/%Y'),'Histórico (kWh)':np.nan,'Previsão (kWh)':pred})
        st.line_chart(pd.concat([hist,pred_df],ignore_index=True).set_index('Mês'),y_label='kWh')
        st.caption('Linha histórica e linha prevista representam séries distintas. A tabela abaixo identifica cada mês.')
        last_tariff=float(df.tarifa.iloc[-1]);result=pd.DataFrame({'Mês':[f'{MONTHS[d.month-1]}/{d.year}' for d in dates],'Consumo previsto':[num(v)+' kWh' for v in pred],'Custo estimado':[money(v*last_tariff) for v in pred]})
        st.dataframe(result,hide_index=True,use_container_width=True)
        if len(df)>=6:
            cut=max(3,int(len(df)*.8));valid=LinearRegression().fit(x[:cut],y[:cut]);mae=mean_absolute_error(y[cut:],np.maximum(0,valid.predict(x[cut:])))
            st.metric('Erro absoluto médio da validação',num(mae)+' kWh')
            st.caption('Avaliação simples nos registros finais, sem garantia de precisão futura.')
        st.warning('Este modelo usa regressão linear. Ainda não considera sazonalidade, clima ou diferenças regionais do Brasil. Com poucos meses de dados, a previsão pode ter erro elevado.')

elif page=='Simulador de economia':
    st.write('Calcule uma estimativa de economia reduzindo o tempo de uso diário de um equipamento.')
    equip=st.selectbox('Equipamento',['Chuveiro elétrico','Ar-condicionado','Ventilador','Televisão','Outro'])
    powers={'Chuveiro elétrico':5500,'Ar-condicionado':1200,'Ventilador':80,'Televisão':120,'Outro':500}
    power=st.number_input('Potência (W)',min_value=0,value=powers[equip],step=10)
    hours=st.number_input('Horas de uso por dia',min_value=0.,max_value=24.,value=2.,step=.25)
    reduction=st.number_input('Redução diária (minutos)',min_value=0,max_value=1440,value=30,step=5)
    days=st.number_input('Dias de utilização por mês',min_value=1,max_value=31,value=30)
    tariff=st.number_input('Tarifa para simulação (R$/kWh)',min_value=0.,value=.9,step=.01,format='%.2f')
    if reduction>hours*60:st.error('A redução não pode ultrapassar o tempo diário de uso.')
    else:
        saved=power/1000*reduction/60*days
        a,b=st.columns(2);a.metric('Economia potencial mensal',num(saved,2)+' kWh');b.metric('Economia financeira mensal',money(saved*tariff))
        st.caption('Simulação teórica. O consumo real pode variar conforme o aparelho e as condições de uso.')

else:
    st.write('**Energia em Foco** é um Projeto Integrador acadêmico da UNIVESP voltado à análise do consumo residencial de energia elétrica.')
    st.write('O sistema permite cadastrar consumos mensais, visualizar gráficos por ano, estimar consumos futuros por regressão linear e simular economia de energia.')
    st.write('Os dados da demonstração são fictícios e temporários. As contas pessoais utilizam nome de usuário e senha, sem solicitar e-mail, CPF ou telefone.')
    st.warning('As previsões são demonstrativas e não incorporam clima, sazonalidade ou tarifas completas da distribuidora. Não substituem a conta de energia.')
    if st.session_state.mode=='account':
        st.subheader('Excluir minha conta e meus dados')
        st.write('A exclusão remove os registros salvos e a conta. Essa ação não pode ser desfeita.')
        with st.form('delete_account'):
            password=st.text_input('Confirme sua senha para excluir',type='password')
            confirm=st.checkbox('Entendo que a exclusão é definitiva')
            if st.form_submit_button('Excluir minha conta e todos os dados'):
                try:
                    if not confirm or storage.authenticate(st.session_state.username,password)!=st.session_state.uid: st.error('Confirme a exclusão e informe a senha correta.')
                    else:
                        storage.delete_account(st.session_state.uid)
                        st.session_state.mode='home';st.session_state.uid=None;st.session_state.username=None
                        flash('Conta excluída.');st.rerun()
                except Exception: st.error('Não foi possível excluir a conta.')
